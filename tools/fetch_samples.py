"""Acquire unchanged, checksum-pinned public specification and application fixtures."""

import argparse
import hashlib
import io
import json
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

SOURCES = {
    "spec": {
        "repository": "Azure/opendigitaltwins-dtdl",
        "revision": "d19669a438a63be377c3cfc2fcabeac2e16ad55b",
        "sha256": "e05d1b2a27357d7db0952abd385f07172a9560c42320db471e05ce7c8949f3fb",
        "directory": "DTDL/v3/spec/",
        "license": "CC-BY-4.0",
    },
    "parser": {
        "repository": "digitaltwinconsortium/DTDLParser",
        "revision": "c368fb0828aa7944747d147c1bf6e3999c095f62",
        "sha256": "4e01899201a79fb57fa63e4bf3d627ceda1695a87f61e0d880fc6bb3a49b16e8",
        "directory": "samples/DTDLParserResolveSample/dtmi/",
        "license": "MIT",
    },
}
MAX_BYTES = 128 * 1024 * 1024


def unpack(data: bytes, destination: Path, source: dict) -> dict:
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError("Archive checksum mismatch; nothing extracted.")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination}")
    prefix = f"{source['repository'].split('/')[-1]}-{source['revision']}/"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        stage = Path(temporary) / "fixture"
        stage.mkdir()
        fingerprints = {}
        total = 0
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.startswith(prefix):
                    continue
                relative = entry.filename.removeprefix(prefix)
                if relative != "LICENSE" and not (
                    relative.startswith(source["directory"]) and relative.endswith(".json")
                ):
                    continue
                path = PurePosixPath(relative)
                if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
                    raise ValueError(f"Unsafe archive path: {relative}")
                total += entry.file_size
                if total > MAX_BYTES or relative in fingerprints:
                    raise ValueError("Archive exceeds size bounds or repeats a fixture path.")
                content = archive.read(entry)
                target = stage.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                fingerprints[relative] = hashlib.sha256(content).hexdigest()
        if "LICENSE" not in fingerprints or len(fingerprints) < 2:
            raise ValueError("Archive lacks expected fixtures or license.")
        manifest = {**source, "files": dict(sorted(fingerprints.items()))}
        (stage / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        stage.rename(destination)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=SOURCES)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = SOURCES[args.source]
    url = f"https://codeload.github.com/{source['repository']}/zip/{source['revision']}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Archive exceeds download bound.")
        result = unpack(data, args.destination, source)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Fixture acquisition failed: {error}", file=sys.stderr)
        return 1
    print(f"Acquired {len(result['files']) - 1} unchanged files from {source['repository']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
