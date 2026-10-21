"""Explicit, checksum-pinned integration fixture acquisition; not runtime resolution."""

import argparse
import hashlib
import io
import json
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REVISION = "1d19b2584df02e05714628a57a7ddd69edeef29c"
URL = f"https://codeload.github.com/WillowInc/opendigitaltwins-building/zip/{REVISION}"
SHA256 = "13be79b36c06c32711c73f778ff50e1baee51833d2dc143fc19a958765c01044"
PREFIX = f"opendigitaltwins-building-{REVISION}/"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


def unpack(data: bytes, destination: Path, expected_hash: str = SHA256) -> dict:
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("Willow archive checksum mismatch; no files extracted.")
    if destination.exists():
        raise ValueError(f"Fixture destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = {}
    total = 0
    with tempfile.TemporaryDirectory(prefix=".willow-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "fixture"
        stage.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for entry in sorted(archive.infolist(), key=lambda item: item.filename):
                if entry.is_dir() or not entry.filename.startswith(PREFIX):
                    continue
                relative = entry.filename.removeprefix(PREFIX)
                if relative != "LICENSE" and not (
                    relative.startswith("Ontology/") and relative.endswith(".json")
                ):
                    continue
                path = PurePosixPath(relative)
                if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
                    raise ValueError(f"Unsafe archive path: {relative}")
                total += entry.file_size
                if total > 128 * 1024 * 1024:
                    raise ValueError("Expanded fixture exceeds 128 MiB.")
                content = archive.read(entry)
                target = stage.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                fingerprints[relative] = hashlib.sha256(content).hexdigest()
        if "LICENSE" not in fingerprints or len(fingerprints) < 2:
            raise ValueError("Archive does not contain the expected ontology and license.")
        manifest = {"revision": REVISION, "archive_sha256": expected_hash, "files": fingerprints}
        (stage / "fixture.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        stage.rename(destination)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(MAX_ARCHIVE_BYTES + 1)
        if len(data) > MAX_ARCHIVE_BYTES:
            raise ValueError("Fixture archive exceeds 64 MiB.")
        manifest = unpack(data, args.destination)
    except (OSError, ValueError, zipfile.BadZipFile, urllib.error.URLError) as error:
        print(f"Fixture acquisition failed: {error}", file=sys.stderr)
        return 1
    print(f"Acquired {len(manifest['files']) - 1} model files at revision {REVISION}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
