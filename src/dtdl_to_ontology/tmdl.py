"""Small serializer for documented ontology TMDL constructs, without bindings."""

import json
import re

from .naming import (
    NameOverrides,
    annotation_text,
    doc_comments,
    lineage,
    property_name,
    quote,
    target_name,
)
from .plan import EntityPlan, Plan, PropertyPlan


def json_assignment(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def render_annotations(annotations: dict[str, str], indent: str) -> list[str]:
    return [
        f"{indent}annotation {quote(name)} = {annotation_text(value)}"
        for name, value in sorted(annotations.items())
    ]


def render_property(
    entity: str, prop: PropertyPlan, overrides: NameOverrides | None = None
) -> list[str]:
    lines = doc_comments(prop.description, "\t")
    lines.extend(
        [
            f"\tproperty {quote(property_name(entity, prop.name, overrides))}",
            f"\t\tlineageTag: {lineage(entity + '/' + prop.name, 'property')}",
        ]
    )
    if prop.logical_type["kind"] == "primitive":
        lines.append(f"\t\tdataType: {prop.logical_type['dataType']}")
    else:
        lines.extend(
            [
                "\t\tdataType: complex",
                f"\t\tcomplexDataType = {json_assignment(prop.logical_type)}",
            ]
        )
    lines.extend(render_annotations(prop.annotations, "\t\t"))
    return lines


def render_entity(entity: EntityPlan, overrides: NameOverrides | None = None) -> str:
    name = target_name(entity.identity, overrides=overrides)
    lines = doc_comments(entity.description)
    lines.extend([f"entity {quote(name.qualified)}", f"\tlineageTag: {name.lineage_tag}"])
    if entity.base:
        base = target_name(entity.base, overrides=overrides).qualified
        lines.append(f"\tbaseEntityType: {quote(base)}")
    lines.extend(render_annotations(entity.annotations, "\t"))
    for prop in sorted(entity.properties, key=lambda prop: prop.name):
        lines.append("")
        lines.extend(render_property(entity.identity, prop, overrides))
    return "\n".join(lines) + "\n"


def render_relationships(plan: Plan) -> str:
    if plan.blocked:
        raise ValueError("Cannot render a relationship plan with blocking findings.")
    if plan.relationships and not plan.profile.relationships_enabled:
        raise ValueError("Unbound relationship output is unverified for this profile.")
    lines = []
    for relation in sorted(plan.relationships, key=lambda relation: relation.identity):
        overrides = plan.options.name_overrides
        name = target_name(relation.identity, "relationship", overrides)
        source = target_name(relation.from_entity, overrides=overrides).qualified
        target = target_name(relation.to_entity, overrides=overrides).qualified
        if lines:
            lines.append("")
        lines.extend(doc_comments(relation.description))
        lines.extend(
            [
                f"entityRelationship {quote(name.qualified)}",
                f"\tlineageTag: {name.lineage_tag}",
                f"\tfromEntity: {quote(source)}",
                f"\ttoEntity: {quote(target)}",
            ]
        )
        if relation.label:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", relation.label):
                raise ValueError("Relationship labels must be source programming names.")
            lines.append(f"\tlabel: {relation.label}")
        lines.extend(render_annotations(relation.annotations, "\t"))
    return "\n".join(lines) + ("\n" if lines else "")
