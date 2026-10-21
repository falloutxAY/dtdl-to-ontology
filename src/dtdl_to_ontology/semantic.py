"""Normalized comparison for the ontology TMDL constructs emitted by this package."""

import json
import re
from pathlib import PurePosixPath

_DECLARATION = re.compile(r"^\s*(namespace|entityRelationship|entity|property)\s+(.+?)\s*$")
_IDENTIFIER = re.compile(r"^'(.*)'$")


def _identifier(value: str) -> str:
    match = _IDENTIFIER.fullmatch(value)
    if match:
        return match.group(1).replace("''", "'")
    return value


def _assignment(value: str, separator: str) -> tuple[str, str]:
    key, found, content = value.partition(separator)
    if not found:
        raise ValueError(f"Malformed TMDL assignment: {value!r}.")
    return _identifier(key.strip()), content.strip()


def parse_tmdl(parts: dict[str, str]) -> dict:
    """Extract comparable names and supported semantic fields from TMDL definition parts."""
    result = {"namespaces": {}, "entities": {}, "relationships": {}}
    current_record = None
    current_entity = None
    pending_docs: list[str] = []

    for path, text in sorted(parts.items()):
        if PurePosixPath(path).suffix.lower() != ".tmdl":
            continue
        current_record = None
        current_entity = None
        pending_docs = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("///"):
                pending_docs.append(stripped[3:].removeprefix(" ").rstrip())
                continue
            declaration = _DECLARATION.match(line)
            if declaration:
                kind, raw_name = declaration.groups()
                name = _identifier(raw_name)
                description = "\n".join(pending_docs)
                pending_docs = []
                if kind == "namespace":
                    record = {"name": name}
                    _insert_unique(result["namespaces"], name, record, path, line_number)
                elif kind == "entity":
                    namespace, separator, _ = name.partition("#")
                    record = {
                        "name": name,
                        "namespace": namespace if separator else "",
                        "properties": {},
                    }
                    if description:
                        record["description"] = description
                    _insert_unique(result["entities"], name, record, path, line_number)
                    current_entity = record
                elif kind == "entityRelationship":
                    record = {"name": name}
                    if description:
                        record["description"] = description
                    _insert_unique(result["relationships"], name, record, path, line_number)
                    current_entity = None
                else:
                    if current_entity is None:
                        raise ValueError(f"Property outside an entity in {path}:{line_number}.")
                    record = {"name": name}
                    if description:
                        record["description"] = description
                    _insert_unique(current_entity["properties"], name, record, path, line_number)
                current_record = record
                continue
            if not stripped or stripped.startswith("//"):
                continue
            if current_record is None:
                continue
            if stripped.startswith("lineageTag:"):
                current_record["lineageTag"] = stripped.partition(":")[2].strip()
            elif stripped.startswith("dataType:"):
                current_record["dataType"] = stripped.partition(":")[2].strip()
            elif stripped.startswith("baseEntityType:"):
                current_record["baseEntityType"] = _identifier(stripped.partition(":")[2].strip())
            elif stripped.startswith("fromEntity:"):
                current_record["fromEntity"] = _identifier(stripped.partition(":")[2].strip())
            elif stripped.startswith("toEntity:"):
                current_record["toEntity"] = _identifier(stripped.partition(":")[2].strip())
            elif stripped.startswith("complexDataType ="):
                value = stripped.partition("=")[2].strip()
                try:
                    current_record["complexDataType"] = json.loads(value)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Malformed complexDataType JSON in {path}:{line_number}."
                    ) from error
            elif stripped.startswith("annotation "):
                assignment = stripped.removeprefix("annotation ")
                key, value = _assignment(assignment, "=")
                if key in current_record.get("annotations", {}):
                    raise ValueError(f"Duplicate annotation {key!r} in {path}:{line_number}.")
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Malformed annotation in {path}:{line_number}.") from error
                current_record.setdefault("annotations", {})[key] = parsed_value
            else:
                raise ValueError(
                    f"Unsupported TMDL construct in {path}:{line_number}: {stripped!r}."
                )

    for entity in result["entities"].values():
        entity["properties"] = dict(sorted(entity["properties"].items()))
    return {key: dict(sorted(value.items())) for key, value in result.items()}


def _insert_unique(target: dict, key: str, record: dict, path: str, line_number: int) -> None:
    if key in target:
        raise ValueError(f"Duplicate TMDL {record['name']!r} in {path}:{line_number}.")
    target[key] = record


def _compare_records(before: dict, after: dict, *, ignored: frozenset[str] = frozenset()) -> dict:
    return {
        key: {"submitted": before.get(key), "returned": after.get(key)}
        for key in sorted((before.keys() | after.keys()) - ignored)
        if before.get(key) != after.get(key)
    }


def _compare_nested(before: dict, after: dict) -> dict:
    before_keys, after_keys = before.keys(), after.keys()
    changed = {}
    for key in sorted(before_keys & after_keys):
        difference = _compare_records(before[key], after[key], ignored=frozenset({"properties"}))
        if difference:
            changed[key] = difference
    return {
        "missing": sorted(before_keys - after_keys),
        "additional": sorted(after_keys - before_keys),
        "changed": changed,
    }


def compare_semantics(
    submitted_parts: dict[str, str],
    returned_parts: dict[str, str],
    *,
    manifest: object = None,
) -> dict:
    """Compare normalized supported TMDL semantics, not TMDL equivalence in general."""
    submitted = parse_tmdl(submitted_parts)
    returned = parse_tmdl(returned_parts)

    entity_diffs = _compare_nested(submitted["entities"], returned["entities"])
    property_changes = {}
    for entity_name in sorted(submitted["entities"].keys() & returned["entities"].keys()):
        before_properties = submitted["entities"][entity_name]["properties"]
        after_properties = returned["entities"][entity_name]["properties"]
        difference = _compare_nested(before_properties, after_properties)
        if difference["missing"] or difference["additional"] or difference["changed"]:
            property_changes[entity_name] = difference

    differences = {
        "namespaces": _compare_nested(submitted["namespaces"], returned["namespaces"]),
        "entities": entity_diffs,
        "properties": property_changes,
        "relationships": _compare_nested(submitted["relationships"], returned["relationships"]),
    }
    equal = (
        not any(
            category["missing"] or category["additional"] or category["changed"]
            for category in (
                differences["namespaces"],
                differences["entities"],
                differences["relationships"],
            )
        )
        and not property_changes
    )

    loss_context = None
    if isinstance(manifest, dict):
        findings = manifest.get("transformations_and_findings", [])
        grouped_losses = {}
        if isinstance(findings, list):
            for finding in findings:
                if (
                    not isinstance(finding, dict)
                    or finding.get("approved") is not True
                    or finding.get("selected") is not True
                ):
                    continue
                code = finding.get("code", "unknown")
                policy = finding.get("policy")
                key = (code, policy)
                entry = grouped_losses.setdefault(
                    key,
                    {"code": code, "policy": policy, "count": 0, "source_examples": []},
                )
                entry["count"] += 1
                if len(entry["source_examples"]) < 3:
                    entry["source_examples"].append(
                        {"dtmi": finding.get("dtmi"), "source": finding.get("source")}
                    )
        loss_context = {
            "selected_policies": sorted(
                policy for policy in manifest.get("policies", []) if isinstance(policy, str)
            ),
            "intentional_mapping_losses": [
                grouped_losses[key]
                for key in sorted(grouped_losses, key=lambda item: (item[0], item[1] or ""))
            ],
        }
    return {
        "status": "completed",
        "scope": "normalized emitted TMDL fields; not full semantic equivalence",
        "supported_fields_match": equal,
        "differences": differences,
        "mapping_loss_context": loss_context,
    }
