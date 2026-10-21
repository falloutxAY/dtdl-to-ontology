"""Publish a complete sibling staging directory without overwriting prior results."""

import shutil
import tempfile
from pathlib import Path

from .definition import envelope, write_parts
from .report import canonical_json, readable_report


def ensure_destination(destination: Path) -> None:
    if destination.is_symlink():
        raise ValueError("Output destination must not be a symbolic link.")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError(
            f"Output destination is not an empty directory: {destination}. "
            "Any prior result is unchanged; choose a new output location."
        )


def publish(
    destination: Path,
    report: dict,
    manifest: dict,
    parts: dict[str, str] | None,
) -> None:
    destination = destination.absolute()
    ensure_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    try:
        for filename, value in (("report.json", report), ("manifest.json", manifest)):
            (stage / filename).write_text(canonical_json(value), encoding="utf-8", newline="\n")
        (stage / "report.md").write_text(readable_report(report), encoding="utf-8", newline="\n")
        if parts is not None:
            if (
                not report["selected_mapping_ready"]
                or report["emission_status"] != "locally_validated"
            ):
                raise ValueError("A ready payload requires a locally validated, unblocked report.")
            write_parts(parts, stage / "parts")
            (stage / "definition.json").write_text(
                canonical_json(envelope(parts)),
                encoding="utf-8",
                newline="\n",
            )
        ensure_destination(destination)
        if destination.exists():
            destination.rmdir()
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
