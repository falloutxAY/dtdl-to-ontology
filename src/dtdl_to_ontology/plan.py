"""Explicit logical target plan; a plan with blockers must never be published."""

from dataclasses import dataclass, field, replace
from typing import Any

from .extensions import semantics
from .geo import GEOSCHEMAS
from .model import Finding, Source
from .options import Options
from .profile import DEFAULT_PROFILE, TargetProfile
from .resolver import Declaration, Resolution, types
from .selection import Selection, select
from .vocabulary import UNIT_VALUES


@dataclass
class PropertyPlan:
    name: str
    source: Source
    owner: str
    logical_type: dict[str, Any]
    description: str = ""
    original: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    pre_fallback_logical_type: dict[str, Any] | None = None


@dataclass
class EntityPlan:
    identity: str
    source: Source
    description: str = ""
    properties: list[PropertyPlan] = field(default_factory=list)
    base: str | None = None
    placeholder: bool = False
    role: str = "interface"
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass
class RelationshipPlan:
    identity: str
    from_entity: str
    to_entity: str
    source: Source
    description: str = ""
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass
class Plan:
    selection: Selection
    options: Options
    profile: TargetProfile
    entities: dict[str, EntityPlan] = field(default_factory=dict)
    relationships: list[RelationshipPlan] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(f.blocking for f in self.findings)


def description(raw: dict) -> str:
    value = raw.get("description", "")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("en"), str):
            return value["en"]
        return next((value[key] for key in sorted(value) if isinstance(value[key], str)), "")
    return ""


class Planner:
    def __init__(
        self,
        selection: Selection,
        options: Options,
        profile: TargetProfile = DEFAULT_PROFILE,
    ):
        self.plan = Plan(
            selection,
            options,
            replace(profile, inheritance=options.inheritance),
            findings=list(selection.findings),
        )
        self.projection_steps = 0

    def projection_budget(self, declaration: Declaration, owner: str) -> bool:
        self.projection_steps += 1
        if self.projection_steps == 1_000_001:
            self.plan.findings.append(
                Finding(
                    "RESOLUTION_LIMIT",
                    "Projection exceeds one million schema/component steps.",
                    declaration.source,
                    owner,
                )
            )
        return self.projection_steps <= 1_000_000

    def loss(
        self,
        code: str,
        message: str,
        declaration: Declaration,
        owner: str,
        policy: str,
        limitation: str,
    ) -> None:
        self.plan.findings.append(
            self.plan.options.loss(
                code,
                message,
                declaration.source,
                owner,
                policy,
                f"Explicitly approve {policy} or select a faithful subset.",
                limitation,
                selected=owner in self.plan.selection.selected,
            )
        )

    def schema(
        self,
        schema: Any,
        declaration: Declaration,
        owner: str,
        stack: tuple[str, ...] = (),
        depth: int = 0,
    ) -> dict | None:
        if not self.projection_budget(declaration, owner):
            return None
        if depth > 128:
            self.plan.findings.append(
                Finding(
                    "SCHEMA_LIMIT",
                    "Schema projection exceeds 128 levels.",
                    declaration.source,
                    owner,
                )
            )
            return None
        if isinstance(schema, str):
            if schema in GEOSCHEMAS:
                self.plan.findings.append(
                    Finding(
                        "GEOSPATIAL_MAPPING",
                        f"Standard geometry {schema} has no faithful native target representation.",
                        declaration.source,
                        owner,
                        workaround="Add native geometry/coordinate collection support to Ontology.",
                        limitation=(
                            "No geometry datatype or coordinate-array typing is provided; "
                            "spatial queries are unsupported and no fallback is introduced."
                        ),
                    )
                )
                return None
            primitives = {
                "string": "string",
                "boolean": "boolean",
                "integer": "int64",
                "long": "int64",
                "float": "double",
                "double": "double",
                "dateTime": "dateTime",
            }
            if schema in primitives:
                if schema in {"integer", "float"}:
                    self.loss(
                        "SOURCE_WIDTH",
                        f"{schema} width is not enforced by the target.",
                        declaration,
                        owner,
                        "metadata-semantics",
                        "Source numeric width requires external validation.",
                    )
                return {"kind": "primitive", "dataType": primitives[schema]}
            if schema in {"date", "time", "duration"}:
                self.loss(
                    "TEMPORAL_STRING",
                    f"{schema} is represented as an ISO string.",
                    declaration,
                    owner,
                    "temporal-strings",
                    "No equivalent native temporal primitive or operations.",
                )
                return {"kind": "primitive", "dataType": "string"}
            if schema in UNIT_VALUES:
                self.loss(
                    "ENUM_UNDERLYING",
                    f"Extension unit vocabulary {schema} becomes string.",
                    declaration,
                    owner,
                    "enum-underlying",
                    "Allowed unit values require external validation.",
                )
                return {"kind": "primitive", "dataType": "string"}
            definition = self.plan.selection.resolution.schemas.get(schema)
            if definition and schema not in stack:
                self.metadata(definition, owner)
                return self.schema(
                    definition.raw,
                    definition,
                    owner,
                    (*stack, schema),
                    depth + 1,
                )
            return None
        if not isinstance(schema, dict):
            return None
        kinds = types(schema)
        if kinds & {"Array", "Map"}:
            self.loss(
                "COLLECTION",
                "Collection is represented as serialized JSON in a string.",
                declaration,
                owner,
                "json-collections",
                "No native typed collection or element querying.",
            )
            return {"kind": "primitive", "dataType": "string"}
        if "Enum" in kinds:
            self.loss(
                "ENUM_UNDERLYING",
                "Enum is represented by its underlying primitive.",
                declaration,
                owner,
                "enum-underlying",
                "Allowed values and labels require external validation.",
            )
            return self.schema(schema.get("valueSchema"), declaration, owner, stack, depth + 1)
        if "Object" in kinds:
            fields = []
            complete = True
            source_fields = schema.get("fields", [])
            for index, item in enumerate(source_fields if isinstance(source_fields, list) else []):
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    complete = False
                    continue
                source = declaration.source
                if schema is not declaration.raw:
                    source = source.child("schema")
                child = Declaration(declaration.owner, item, source.child("fields", index))
                self.metadata(child, owner)
                mapped = self.schema(item.get("schema"), child, owner, stack, depth + 1)
                if mapped is not None:
                    fields.append({"name": item["name"], "type": mapped})
                else:
                    complete = False
            if fields and complete:
                return {"kind": "struct", "fields": fields}
            self.plan.findings.append(
                Finding(
                    "EMPTY_STRUCT",
                    "Fabric requires a nonempty supported struct.",
                    declaration.source,
                    owner,
                )
            )
        return None

    def property(self, declaration: Declaration, owner: str) -> PropertyPlan | None:
        raw = declaration.raw
        self.metadata(declaration, owner)
        if not isinstance(raw.get("name"), str):
            self.plan.findings.append(
                Finding(
                    "PROPERTY_MAPPING",
                    "Property has no valid name.",
                    declaration.source,
                    owner,
                )
            )
            return None
        shape = self.schema(raw.get("schema"), declaration, owner)
        if shape is None:
            self.plan.findings.append(
                Finding(
                    "PROPERTY_MAPPING",
                    "Property schema has no complete target mapping.",
                    declaration.source,
                    owner,
                )
            )
            return None
        return PropertyPlan(
            raw["name"],
            declaration.source,
            declaration.owner,
            shape,
            description(raw),
            self.plan.selection.resolution.collection.original_elements.get(id(raw), raw),
        )

    def metadata(self, declaration: Declaration, owner: str) -> None:
        raw = declaration.raw
        fields = set(raw) & {
            "displayName",
            "comment",
            "unit",
            "writable",
            "annotates",
            "overrides",
            "minMultiplicity",
            "maxMultiplicity",
            "minValue",
            "maxValue",
            "minLength",
            "maxLength",
        }
        if isinstance(raw.get("description"), dict) and len(raw["description"]) > 1:
            fields.add("localized-description")
        if len(types(raw)) > 1:
            fields.add("semantic-types")
        if fields:
            self.loss(
                "METADATA_SEMANTICS",
                f"Manifest-only source semantics: {', '.join(sorted(fields))}.",
                declaration,
                owner,
                "metadata-semantics",
                "Metadata does not enforce constraints, units, overrides or localized display.",
            )

    def component(
        self,
        declaration: Declaration,
        owner: str,
        path: tuple[str, ...],
        stack: tuple[str, ...],
    ) -> dict | None:
        if not self.projection_budget(declaration, owner):
            return None
        target = declaration.raw.get("schema")
        if not isinstance(target, str):
            return None
        if target in stack or len(stack) >= 128:
            self.plan.findings.append(
                Finding(
                    "COMPONENT_CYCLE",
                    "Component projection is recursive or exceeds 128 levels.",
                    declaration.source,
                    owner,
                )
            )
            return None
        self.loss(
            "COMPONENT",
            f"Component {'/'.join(path)} is projected as a fixed property struct.",
            declaration,
            owner,
            "component-properties",
            "Component-scoped structure and contained edge semantics are projected; "
            "DTDL components are by-value, not independent twins.",
        )
        self.metadata(declaration, owner)
        fields = []
        for name, child in self.plan.selection.resolution.contents.get(target, {}).items():
            kinds = types(child.raw)
            child_path = (*path, name)
            shape = None
            if kinds & {"Property", "Telemetry"}:
                self.content_runtime(child, owner)
                prop = self.property(child, owner)
                shape = prop.logical_type if prop else None
            elif "Component" in kinds:
                shape = self.component(child, owner, child_path, (*stack, target))
            elif "Relationship" in kinds:
                if f"{owner}/{'/'.join(child_path)}" not in self.plan.options.omissions:
                    self.plan.findings.append(
                        Finding(
                            "COMPONENT_RELATIONSHIP",
                            f"Contained edge {'/'.join(child_path)} requires explicit omission.",
                            child.source,
                            owner,
                            workaround="Approve omission using the exact component-path selector.",
                            limitation="A contained-instance edge is not an edge on its owner.",
                        )
                    )
                self.metadata(child, owner)
            elif "Command" in kinds:
                self.content_runtime(child, owner)
            if shape is not None:
                fields.append({"name": name, "type": shape})
        if not fields:
            self.plan.findings.append(
                Finding(
                    "EMPTY_STRUCT",
                    "Component has no representable property fields.",
                    declaration.source,
                    owner,
                )
            )
            return None
        return {"kind": "struct", "fields": fields}

    def content_runtime(self, declaration: Declaration, owner: str) -> None:
        kinds = types(declaration.raw)
        if "Telemetry" in kinds:
            self.loss(
                "TELEMETRY_BINDING",
                "Telemetry is retained only as an unbound property.",
                declaration,
                owner,
                "metadata-semantics",
                "No definition-payload-only solution provides ingestion or stream correlation.",
            )
        if "Command" in kinds:
            self.plan.findings.append(
                Finding(
                    "COMMAND_RUNTIME",
                    "Command execution has no definition-payload-only solution.",
                    declaration.source,
                    owner,
                    workaround="Implement command execution in an external device integration.",
                    limitation="Metadata preservation does not execute or synchronize commands.",
                )
            )

    def entity_properties(self, identifier: str, entity: EntityPlan) -> None:
        resolution = self.plan.selection.resolution
        model = resolution.collection.models[identifier]
        declaration = Declaration(identifier, model.raw, model.source)
        self.metadata(declaration, identifier)
        parents = resolution.parents.get(identifier, [])
        inherited = set()
        if parents:
            if self.plan.profile.inheritance:
                if len(parents) != 1:
                    self.plan.findings.append(
                        Finding(
                            "NATIVE_MULTIPLE_INHERITANCE",
                            "Native inheritance cannot select one of multiple parents.",
                            model.source,
                            identifier,
                            workaround="Disable native mode; approve flatten-inheritance.",
                            limitation="The current public TMDL contract has one baseEntityType.",
                        )
                    )
                else:
                    entity.base = parents[0]
                    inherited = set(resolution.contents.get(parents[0], {}))
            else:
                self.loss(
                    "INHERITANCE",
                    "Effective contents are materialized without native ancestry.",
                    declaration,
                    identifier,
                    "flatten-inheritance",
                    "Native type relationships and inherited polymorphism are lost.",
                )
        for name, content in resolution.contents.get(identifier, {}).items():
            if name in inherited:
                if "Component" in types(content.raw):
                    self.component(content, identifier, (name,), (identifier,))
                continue
            self.content_runtime(content, identifier)
            if types(content.raw) & {"Property", "Telemetry"}:
                prop = self.property(content, identifier)
                if prop:
                    entity.properties.append(prop)
            elif "Component" in types(content.raw):
                shape = self.component(content, identifier, (name,), (identifier,))
                if shape:
                    entity.properties.append(
                        PropertyPlan(
                            name,
                            content.source,
                            content.owner,
                            shape,
                            description(content.raw),
                            content.raw,
                        )
                    )

    def reify(self, key: str, owner: str, target: str, declaration: Declaration) -> None:
        identity = key + "#edge"
        edge = EntityPlan(
            identity,
            declaration.source,
            description(declaration.raw),
            role="relationship-instance",
        )
        edge.properties.append(
            PropertyPlan(
                "__dtdl_edge_id",
                declaration.source,
                owner,
                {"kind": "primitive", "dataType": "string"},
                "Runtime edge identifier must be provided by a future data binding.",
            )
        )
        for index, raw in enumerate(declaration.raw.get("properties", [])):
            if not isinstance(raw, dict):
                continue
            source = declaration.source.child("properties", index)
            if raw.get("name") == "__dtdl_edge_id":
                self.plan.findings.append(
                    Finding(
                        "EDGE_ID_COLLISION",
                        "Source edge property collides with generated edge ID.",
                        source,
                        owner,
                    )
                )
                continue
            prop = self.property(Declaration(declaration.owner, raw, source), owner)
            if prop:
                edge.properties.append(prop)
        self.plan.entities[identity] = edge
        self.plan.relationships.extend(
            [
                RelationshipPlan(key + "#source", identity, owner, declaration.source),
                RelationshipPlan(key + "#target", identity, target, declaration.source),
            ]
        )

    def relationships(self) -> None:
        plan = self.plan
        resolution = plan.selection.resolution
        for owner in sorted(plan.selection.selected):
            for name, declaration in resolution.contents.get(owner, {}).items():
                raw = declaration.raw
                if "Relationship" not in types(raw):
                    continue
                key = f"{owner}/{name}"
                if key in plan.options.omissions:
                    continue
                self.metadata(declaration, owner)
                target = plan.options.target_mappings.get(key, raw.get("target"))
                if key in plan.options.target_mappings:
                    plan.findings.append(
                        Finding(
                            "TARGET_MAPPING",
                            f"Explicit target mapping: {key} -> {target}",
                            declaration.source,
                            owner,
                            fidelity="lossy",
                            approved=True,
                            policy="element-target-mapping",
                            workaround="Use the source target when fully available.",
                            limitation="The target constraint is user-specified, not inferred.",
                        )
                    )
                if not isinstance(target, str) or target not in plan.selection.selected:
                    continue
                if not plan.profile.relationships_enabled:
                    plan.findings.append(
                        Finding(
                            "UNBOUND_RELATIONSHIP",
                            "Unbound entity-relationship acceptance has not been established.",
                            declaration.source,
                            owner,
                            fidelity="unverified",
                            workaround="Verify contract acceptance or explicitly omit this edge.",
                            limitation="No backing data is fabricated to bypass the support gate.",
                        )
                    )
                if raw.get("properties"):
                    self.loss(
                        "RELATIONSHIP_PROPERTIES",
                        "Relationship carries instance properties.",
                        declaration,
                        owner,
                        "reify-relationship-properties",
                        "Edge reification is not native attributed-edge semantics.",
                    )
                    if plan.options.permits("reify-relationship-properties"):
                        self.reify(key, owner, target, declaration)
                else:
                    plan.relationships.append(
                        RelationshipPlan(
                            key,
                            owner,
                            target,
                            declaration.source,
                            description(raw),
                        )
                    )

    def unbound_structs(self) -> None:
        plan = self.plan
        for identity, entity in sorted(plan.entities.items()):
            for prop in entity.properties:
                if prop.logical_type["kind"] != "struct":
                    continue
                approved = plan.options.permits("json-objects")
                plan.findings.append(
                    plan.options.loss(
                        "UNBOUND_STRUCT",
                        (
                            f"Struct property {prop.name} is projected as a JSON string."
                            if approved
                            else f"Unbound struct property {prop.name} requires recursive backing."
                        ),
                        prop.source,
                        identity if identity in plan.selection.selected else prop.owner,
                        "json-objects",
                        "Approve json-objects or select scalar-only roots; real backings are "
                        "outside ontology-first scope.",
                        "No native field typing/querying. Downstream ingestion must serialize "
                        "JSON and enforce the source schema; no runtime values are generated.",
                    )
                )
                if approved:
                    prop.pre_fallback_logical_type = prop.logical_type
                    prop.logical_type = {"kind": "primitive", "dataType": "string"}

    def run(self) -> Plan:
        plan = self.plan
        graph = plan.selection.resolution.graph
        if graph:
            for element in graph.elements.values():
                if element.owner not in plan.selection.selected:
                    continue
                context = graph.collection.contexts_at(element.source)
                contract = semantics(element.raw, context)
                for key, code, message in (
                    (
                        "historization",
                        "HISTORIZATION_BINDING",
                        "History capture and historical queries require an explicit "
                        "runtime binding.",
                    ),
                    (
                        "mqtt",
                        "MQTT_RUNTIME",
                        "MQTT transport/serialization semantics have no Ontology "
                        "definition equivalent.",
                    ),
                    (
                        "presence",
                        "FIELD_PRESENCE",
                        "Ontology struct definitions do not enforce DTDL Required field presence.",
                    ),
                ):
                    if key not in contract or (key == "presence" and not contract[key]["required"]):
                        continue
                    plan.findings.append(
                        Finding(
                            code,
                            message,
                            element.source,
                            element.owner,
                            workaround="Implement the required native Ontology capability.",
                            limitation="Source intent is recorded but not implemented "
                            "by target output.",
                        )
                    )
        for identifier in sorted(plan.selection.selected):
            model = plan.selection.resolution.collection.models.get(identifier)
            if model:
                plan.entities[identifier] = EntityPlan(
                    identifier,
                    model.source,
                    description(model.raw),
                )
                self.entity_properties(identifier, plan.entities[identifier])
            elif identifier in plan.options.placeholders:
                source = Source("<configuration>", "/placeholders")
                plan.entities[identifier] = EntityPlan(
                    identifier,
                    source,
                    "Explicit missing-target placeholder; original definition is unavailable.",
                    placeholder=True,
                    role="placeholder",
                )
                plan.findings.append(
                    plan.options.loss(
                        "PLACEHOLDER_TARGET",
                        f"Placeholder for absent definition: {identifier}",
                        source,
                        identifier,
                        "placeholder-targets",
                        "Supply the original target definition.",
                        "A placeholder does not reconstruct source properties or semantics.",
                    )
                )
        for identifier in plan.options.placeholders:
            if identifier in plan.selection.resolution.collection.models:
                plan.findings.append(
                    Finding(
                        "PLACEHOLDER_CONFIG",
                        "Cannot replace an existing definition with a placeholder.",
                        Source("<configuration>", "/placeholders"),
                        identifier,
                    )
                )
        self.relationships()
        self.unbound_structs()
        return plan


def make_plan(
    resolution: Resolution,
    options: Options | None = None,
    profile: TargetProfile = DEFAULT_PROFILE,
) -> Plan:
    options = options or Options()
    selection = select(
        resolution,
        list(options.roots),
        set(options.omissions),
        options.target_mappings,
        set(options.placeholders),
    )
    return Planner(selection, options, profile).run()
