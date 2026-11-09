"""Measure the selected logical target, excluding source/diagnostic sidecars."""

import re
import unicodedata
from dataclasses import dataclass

from .definition import platform_details
from .model import Finding, Source
from .naming import (
    annotation_text,
    lineage,
    namespace_source,
    naming_findings,
    property_name,
    target_name,
)
from .plan import Plan


def json_metrics(value: object) -> tuple[int, int]:
    pending = [(value, 1)]
    nodes = depth = 0
    while pending:
        item, level = pending.pop()
        nodes += 1
        depth = max(depth, level)
        children = (
            item.values() if isinstance(item, dict) else item if isinstance(item, list) else []
        )
        pending.extend((child, level + 1) for child in children)
    return nodes, depth


def complex_metrics(shape: dict) -> tuple[int, int, int]:
    pending = [(shape, 1)]
    nodes = depth = fields = 0
    while pending:
        item, level = pending.pop()
        nodes += 1
        depth = max(depth, level)
        if item["kind"] == "struct":
            fields = max(fields, len(item["fields"]))
            pending.extend((field["type"], level + 1) for field in item["fields"])
        elif item["kind"] == "timeSeries":
            pending.append((item["elementType"], level + 1))
    return nodes, depth, fields


def logical_document(plan: Plan, name: str) -> dict:
    overrides = plan.options.name_overrides
    entities = []
    for identity, entity in sorted(plan.entities.items()):
        properties = []
        for prop in sorted(entity.properties, key=lambda prop: prop.name):
            record = {
                "name": property_name(identity, prop.name, overrides),
                "lineageTag": lineage(identity + "/" + prop.name, "property"),
                "dataType": (
                    prop.logical_type["dataType"]
                    if prop.logical_type["kind"] == "primitive"
                    else "complex"
                ),
            }
            if prop.logical_type["kind"] != "primitive":
                record["complexDataType"] = prop.logical_type
            if prop.description:
                record["description"] = prop.description
            if prop.annotations:
                record["annotations"] = prop.annotations
            properties.append(record)
        record = {
            "name": target_name(identity, overrides=overrides).qualified,
            "lineageTag": target_name(identity).lineage_tag,
            "properties": properties,
        }
        if entity.description:
            record["description"] = entity.description
        if entity.annotations:
            record["annotations"] = entity.annotations
        if entity.base:
            record["baseEntityType"] = target_name(entity.base, overrides=overrides).qualified
        entities.append(record)
    relationships = [
        {
            "name": target_name(r.identity, "relationship", overrides).qualified,
            "lineageTag": target_name(r.identity, "relationship").lineage_tag,
            "fromEntity": target_name(r.from_entity, overrides=overrides).qualified,
            "toEntity": target_name(r.to_entity, overrides=overrides).qualified,
            **({"label": r.label} if r.label else {}),
            **({"description": r.description} if r.description else {}),
            **({"annotations": r.annotations} if r.annotations else {}),
        }
        for r in sorted(plan.relationships, key=lambda r: r.identity)
    ]
    return {
        "compatibilityLevel": 1000000,
        "model": {
            "name": "Model",
            "namespaces": [
                {"name": "default", "lineageTag": "default"},
                *[
                    {
                        "name": namespace,
                        "lineageTag": lineage(original, "namespace"),
                        "annotations": {"dtdlNamespace": original},
                    }
                    for namespace, original in sorted(
                        {
                            target_name(identity, overrides=overrides).namespace: namespace_source(
                                identity
                            )
                            for identity in plan.entities
                            if target_name(identity, overrides=overrides).namespace
                        }.items()
                    )
                ],
            ],
            "entities": entities,
            "entityRelationships": relationships,
        },
        "platform": platform_details(name),
    }


@dataclass
class Preflight:
    findings: list[Finding]
    measurements: dict


def preflight(plan: Plan, name: str = "Ontology") -> Preflight:
    profile = plan.profile
    findings = naming_findings(plan)
    overrides = plan.options.name_overrides
    global_source = Source("<target>")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,88}", name):
        findings.append(
            Finding(
                "ONTOLOGY_NAME",
                "Ontology item name must start with an ASCII letter, contain only "
                "ASCII letters, digits and underscores, and be shorter than 90 characters.",
                global_source,
                limitation="Fabric rejects invalid item names before interpreting the definition.",
            )
        )

    def check(metric: str, measured: int, limit: int, source: Source, owner: str | None) -> None:
        if measured > limit:
            findings.append(
                Finding(
                    f"LIMIT_{metric}",
                    f"Measured {measured}; supported limit is {limit}.",
                    source,
                    owner,
                    workaround="Select a smaller explicit projection or change the mapping.",
                    limitation="REST batching does not bypass per-item capacity limits.",
                )
            )

    def text(value: str, source: Source, owner: str | None, label: str) -> None:
        check("TEXT", len(value), profile.max_text, source, owner)
        if any(unicodedata.category(c) == "Cc" and c not in "\r\n\t" for c in value):
            findings.append(
                Finding(
                    "TEXT_CONTROL",
                    f"{label} contains unsupported control characters.",
                    source,
                    owner,
                )
            )

    def annotations(values: dict[str, str], source: Source, owner: str) -> None:
        check("ANNOTATIONS", len(values), profile.max_annotations, source, owner)
        for key, value in values.items():
            check("NAME", len(key), profile.max_name, source, owner)
            text(value, source, owner, "Annotation")
            try:
                annotation_text(value)
            except ValueError as error:
                findings.append(Finding("ANNOTATION_TEXT", str(error), source, owner))

    check("ENTITIES", len(plan.entities), profile.max_entities, global_source, None)
    check("RELATIONSHIPS", len(plan.relationships), profile.max_relationships, global_source, None)
    check("NAME", len(name), profile.max_name, global_source, None)
    property_counts = {}
    for identity, entity in sorted(plan.entities.items()):
        target = target_name(identity, overrides=overrides)
        check("NAME", len(target.qualified), profile.max_name, entity.source, identity)
        text(entity.description, entity.source, identity, "Description")
        annotations(entity.annotations, entity.source, identity)
        inherited = set()
        pending = [identity]
        while pending:
            current = pending.pop()
            if current in inherited or current not in plan.entities:
                continue
            inherited.add(current)
            base = plan.entities[current].base
            if base:
                pending.append(base)
        count = sum(len(plan.entities[ancestor].properties) for ancestor in inherited)
        property_counts[identity] = count
        check("PROPERTIES", count, profile.max_properties, entity.source, identity)
        for prop in entity.properties:
            mapped = property_name(identity, prop.name, overrides)
            check("NAME", len(mapped), profile.max_name, prop.source, identity)
            text(prop.description, prop.source, identity, "Description")
            annotations(prop.annotations, prop.source, identity)
            if prop.logical_type["kind"] != "primitive":
                nodes, depth, fields = complex_metrics(prop.logical_type)
                check("COMPLEX_NODES", nodes, profile.max_complex_nodes, prop.source, identity)
                check("COMPLEX_DEPTH", depth, profile.max_complex_depth, prop.source, identity)
                check("STRUCT_FIELDS", fields, profile.max_struct_fields, prop.source, identity)
                pending_shapes = [prop.logical_type]
                while pending_shapes:
                    shape = pending_shapes.pop()
                    if shape["kind"] == "struct":
                        for field in shape["fields"]:
                            check(
                                "NAME", len(field["name"]), profile.max_name, prop.source, identity
                            )
                            pending_shapes.append(field["type"])
                    elif shape["kind"] == "timeSeries":
                        pending_shapes.append(shape["elementType"])
    for relation in plan.relationships:
        mapped = target_name(relation.identity, "relationship", overrides).qualified
        check("NAME", len(mapped), profile.max_name, relation.source, relation.from_entity)
        text(relation.label, relation.source, relation.from_entity, "Relationship label")
        text(relation.description, relation.source, relation.from_entity, "Description")
        annotations(relation.annotations, relation.source, relation.from_entity)
    nodes, depth = json_metrics(logical_document(plan, name))
    check("DOCUMENT_NODES", nodes, profile.max_document_nodes, global_source, None)
    check("DOCUMENT_DEPTH", depth, profile.max_document_depth, global_source, None)
    return Preflight(
        findings,
        {
            "entities": len(plan.entities),
            "relationships": len(plan.relationships),
            "properties_per_entity": property_counts,
            "document_nodes": nodes,
            "document_depth": depth,
        },
    )
