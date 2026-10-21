"""Readable TMDL definition parts and their UTF-8 InlineBase64 transport envelope."""

import base64
import uuid
from pathlib import Path, PurePosixPath

from .naming import lineage, quote, target_name
from .plan import Plan
from .report import canonical_json
from .tmdl import render_entity, render_relationships


def platform_details(name: str, logical_id: str | None = None) -> dict:
    if not name.strip():
        raise ValueError("Ontology display name must not be empty.")
    item_id = str(uuid.UUID(logical_id)) if logical_id else lineage(name, "ontology")
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/"
        "gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Ontology", "displayName": name},
        "config": {"version": "2.0", "logicalId": item_id},
    }


def build_parts(plan: Plan, name: str, logical_id: str | None = None) -> dict[str, str]:
    if plan.blocked:
        raise ValueError("Cannot emit a definition with blocking findings.")
    parts = {
        ".platform": canonical_json(platform_details(name, logical_id)),
        "database.tmdl": "database\n\tcompatibilityLevel: 1000000\n",
        "namespaces/default.tmdl": "namespace default\n\tlineageTag: default\n",
    }
    namespaces = {target_name(identity).namespace for identity in plan.entities}
    model_lines = ["model Model", "", "ref namespace default"]
    for namespace in sorted(namespaces):
        parts[f"namespaces/{namespace}.tmdl"] = (
            f"namespace {quote(namespace)}\n\tlineageTag: {lineage(namespace, 'namespace')}\n"
        )
        model_lines.append(f"ref namespace {quote(namespace)}")
    seen = set()
    for identity, entity in sorted(plan.entities.items()):
        target = target_name(identity).qualified
        if target.casefold() in seen:
            raise ValueError(f"Case-insensitive target identity collision: {identity}")
        seen.add(target.casefold())
        parts[f"entities/{target}.tmdl"] = render_entity(entity)
        model_lines.append(f"ref entity {quote(target)}")
    relationships = render_relationships(plan)
    if relationships:
        parts["entityRelationships.tmdl"] = relationships
    parts["model.tmdl"] = "\n".join(model_lines) + "\n"
    return dict(sorted(parts.items()))


def envelope(parts: dict[str, str]) -> dict:
    return {
        "parts": [
            {
                "path": path,
                "payload": base64.b64encode(text.encode("utf-8")).decode("ascii"),
                "payloadType": "InlineBase64",
            }
            for path, text in sorted(parts.items())
        ]
    }


def write_parts(parts: dict[str, str], destination: Path) -> None:
    for path, text in sorted(parts.items()):
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in path:
            raise ValueError(f"Invalid Fabric definition part path: {path}")
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
