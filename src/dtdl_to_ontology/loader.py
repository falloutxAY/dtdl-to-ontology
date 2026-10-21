"""Bounded, offline loading; this is not a general JSON-LD processor."""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .model import Collection, Finding, Model, Source

CORE_CONTEXT = "dtmi:dtdl:context;3"
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_FILES = 20_000
MAX_DEPTH = 128
MAX_NODES = 1_000_000
DTMI = re.compile(r"dtmi:(?:[A-Za-z_][A-Za-z0-9_]*:)*[A-Za-z_][A-Za-z0-9_]*;[1-9]\d*(?:\.\d+)?$")


def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"Non-JSON number: {value}")


def finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"JSON number is outside the supported finite range: {value}")
    return result


def json_bounds(value: Any, max_depth: int = MAX_DEPTH, max_nodes: int = MAX_NODES) -> None:
    pending = [(value, 1)]
    count = 0
    while pending:
        current, depth = pending.pop()
        count += 1
        if count > max_nodes or depth > max_depth:
            raise ValueError(f"JSON exceeds node/depth bounds ({max_nodes}/{max_depth}).")
        if isinstance(current, dict):
            pending.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)


def read_json(data: bytes) -> Any:
    result = json.loads(
        data.decode("utf-8-sig"),
        object_pairs_hook=object_without_duplicates,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )
    json_bounds(result)
    return result


def load(path: Path) -> Collection:
    result = Collection()
    if path.is_symlink():
        result.findings.append(
            Finding("INPUT", "Symlink input is not supported.", Source(path.name))
        )
        return result
    if not path.is_dir() and not path.is_file():
        result.findings.append(Finding("INPUT", "Input does not exist.", Source(path.name)))
        return result
    root = path if path.is_dir() else path.parent
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    if not files or len(files) > MAX_FILES:
        result.findings.append(
            Finding("INPUT_LIMIT", f"Expected 1 to {MAX_FILES} JSON files.", Source(path.name))
        )
        return result
    total = 0
    for file in files:
        source = Source(file.relative_to(root).as_posix())
        try:
            if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
                raise ValueError("Input file escapes the source root or is a symlink.")
            with file.open("rb") as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            total += len(data)
            if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("Input exceeds 16 MiB per file or 128 MiB total.")
            document = read_json(data)
        except (OSError, ValueError, RecursionError) as error:
            result.findings.append(Finding("INPUT", str(error), source))
            continue
        result.fingerprints[source.file] = hashlib.sha256(data).hexdigest()
        entries = document if isinstance(document, list) else [document]
        for index, raw in enumerate(entries):
            location = source.child(index) if isinstance(document, list) else source
            if not isinstance(raw, dict) or raw.get("@type") != "Interface":
                result.findings.append(
                    Finding("INPUT", "Expected a DTDLv3 Interface object.", location)
                )
                continue
            identifier = raw.get("@id")
            if not isinstance(identifier, str) or not DTMI.fullmatch(identifier):
                result.findings.append(Finding("IDENTIFIER", "Invalid interface DTMI.", location))
                continue
            contexts = raw.get("@context", [])
            contexts = [contexts] if isinstance(contexts, str) else contexts
            if not isinstance(contexts, list) or not all(isinstance(c, str) for c in contexts):
                result.findings.append(
                    Finding(
                        "CONTEXT", "Context must be a string or string array.", location, identifier
                    )
                )
                continue
            if CORE_CONTEXT not in contexts or any(
                c.startswith("dtmi:dtdl:context;") and c != CORE_CONTEXT for c in contexts
            ):
                result.findings.append(
                    Finding("VERSION", "Only DTDLv3 context is supported.", location, identifier)
                )
                continue
            previous = result.models.get(identifier)
            if previous:
                if previous.raw != raw:
                    result.findings.append(
                        Finding(
                            "DUPLICATE_ID",
                            f"Conflicting DTMI; first declared at {previous.source}.",
                            location,
                            identifier,
                        )
                    )
                else:
                    previous.sources.append(location)
                continue
            result.models[identifier] = Model(identifier, raw, location, [location])
    result.models = dict(sorted(result.models.items()))
    return result
