"""Small serializer for documented ontology TMDL constructs, without bindings."""

import json

from .naming import doc_comments, lineage, property_name, quote, target_name
from .plan import EntityPlan, Plan, PropertyPlan


def json_assignment(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def render_annotations(annotations: dict[str, str], indent: str) -> list[str]:
    return [
        f"{indent}annotation {quote(name)} = {json_assignment(value)}"
        for name, value in sorted(annotations.items())
    ]


def render_property(entity: str, prop: PropertyPlan) -> list[str]:
    lines = doc_comments(prop.description, "\t")
    lines.extend(
        [
            f"\tproperty {quote(property_name(entity, prop.name))}",
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


def render_entity(entity: EntityPlan) -> str:
    name = target_name(entity.identity)
    lines = doc_comments(entity.description)
    lines.extend([f"entity {quote(name.qualified)}", f"\tlineageTag: {name.lineage_tag}"])
    if entity.base:
        lines.append(f"\tbaseEntityType: {quote(target_name(entity.base).qualified)}")
    lines.extend(render_annotations(entity.annotations, "\t"))
    for prop in sorted(entity.properties, key=lambda prop: prop.name):
        lines.append("")
        lines.extend(render_property(entity.identity, prop))
    return "\n".join(lines) + "\n"


def render_relationships(plan: Plan) -> str:
    if plan.blocked:
        raise ValueError("Cannot render a relationship plan with blocking findings.")
    if plan.relationships and not plan.profile.relationships_enabled:
        raise ValueError("Unbound relationship output is unverified for this profile.")
    lines = []
    for relation in sorted(plan.relationships, key=lambda relation: relation.identity):
        name = target_name(relation.identity, "relationship")
        if lines:
            lines.append("")
        lines.extend(doc_comments(relation.description))
        lines.extend(
            [
                f"entityRelationship {quote(name.qualified)}",
                f"\tlineageTag: {name.lineage_tag}",
                f"\tfromEntity: {quote(target_name(relation.from_entity).qualified)}",
                f"\ttoEntity: {quote(target_name(relation.to_entity).qualified)}",
            ]
        )
        lines.extend(render_annotations(relation.annotations, "\t"))
    return "\n".join(lines) + ("\n" if lines else "")
