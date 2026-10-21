"""Resolve the supported DTDLv3 subset with source-addressable failures."""

import re
from dataclasses import dataclass, field
from typing import Any

from .loader import DTMI
from .model import Collection, Finding, Model, Source
from .vocabulary import (
    ANNOTATION,
    EXTENSIONS,
    OVERRIDING,
    QUANTITATIVE,
    QUANTITY_UNITS,
    UNIT_VALUES,
)

PRIMITIVES = {
    "boolean",
    "date",
    "dateTime",
    "double",
    "duration",
    "float",
    "integer",
    "long",
    "string",
    "time",
}
SCHEMA_KINDS = {"Array", "Enum", "Map", "Object"}
CONTENT_KINDS = {"Property", "Relationship", "Component", "Telemetry", "Command"}
NAME = re.compile(r"[A-Za-z](?:[A-Za-z0-9_]*[A-Za-z0-9])?\Z")


def valid_name(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 512 and NAME.fullmatch(value) is not None


def types(raw: dict) -> set[str]:
    value = raw.get("@type", [])
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


@dataclass(frozen=True)
class Declaration:
    owner: str
    raw: dict[str, Any]
    source: Source


@dataclass(frozen=True, order=True)
class Reference:
    target: str
    reason: str
    source: Source


@dataclass
class Resolution:
    collection: Collection
    schemas: dict[str, Declaration] = field(default_factory=dict)
    contents: dict[str, dict[str, Declaration]] = field(default_factory=dict)
    origins: dict[str, dict[str, list[Declaration]]] = field(default_factory=dict)
    parents: dict[str, list[str]] = field(default_factory=dict)
    references: dict[str, set[Reference]] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


class Resolver:
    def __init__(self, collection: Collection):
        self.result = Resolution(collection)
        self._schema_stack: set[tuple[str, str]] = set()
        self._schema_done: set[tuple[str, str]] = set()
        self._schema_steps = 0
        self._schema_exhausted: set[str] = set()

    def issue(self, code: str, message: str, owner: str, source: Source) -> None:
        self.result.findings.append(Finding(code, message, source, owner))

    def reference(self, owner: str, target: str, reason: str, source: Source) -> None:
        self.result.references.setdefault(owner, set()).add(Reference(target, reason, source))

    def index_schema(self, value: Any, owner: str, source: Source) -> None:
        if isinstance(value, dict):
            identifier = value.get("@id")
            if isinstance(identifier, str) and types(value) & SCHEMA_KINDS:
                declaration = Declaration(owner, value, source)
                previous = self.result.schemas.get(identifier)
                if previous and previous.raw != value:
                    self.issue(
                        "DUPLICATE_SCHEMA",
                        f"Conflicting schema; first declared at {previous.source}.",
                        owner,
                        source,
                    )
                elif not previous:
                    self.result.schemas[identifier] = declaration
            for name, child in value.items():
                self.index_schema(child, owner, source.child(name))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.index_schema(child, owner, source.child(index))

    def schema(self, schema: Any, owner: str, source: Source, depth: int = 0) -> None:
        self._schema_steps += 1
        if self._schema_steps > 1_000_000:
            if owner not in self._schema_exhausted:
                self._schema_exhausted.add(owner)
                self.issue(
                    "RESOLUTION_LIMIT",
                    "Schema validation exceeds one million steps.",
                    owner,
                    source,
                )
            return
        if depth > 128:
            self.issue("RESOLUTION_LIMIT", "Schema depth exceeds 128.", owner, source)
            return
        if isinstance(schema, str):
            if schema in PRIMITIVES:
                return
            if schema in UNIT_VALUES:
                if QUANTITATIVE not in self.result.collection.models[owner].contexts:
                    self.issue(
                        "EXTENSION_CONTEXT",
                        f"{schema} requires quantitativeTypes v1.",
                        owner,
                        source,
                    )
                return
            declaration = self.result.schemas.get(schema)
            if not declaration:
                self.issue("MISSING_SCHEMA", f"Unresolved schema: {schema}", owner, source)
                return
            self.reference(owner, declaration.owner, "schema", source)
            key = (owner, schema)
            if key in self._schema_done:
                return
            if key in self._schema_stack:
                self.issue("SCHEMA_CYCLE", f"Recursive schema: {schema}", owner, source)
                return
            self._schema_stack.add(key)
            findings_before = len(self.result.findings)
            self.schema(declaration.raw, owner, declaration.source, depth + 1)
            self._schema_stack.remove(key)
            if len(self.result.findings) == findings_before:
                self._schema_done.add(key)
            return
        if not isinstance(schema, dict) or len(types(schema) & SCHEMA_KINDS) != 1:
            self.issue("SCHEMA_SHAPE", "Unsupported or missing schema shape.", owner, source)
            return
        kind = next(iter(types(schema) & SCHEMA_KINDS))
        if kind == "Array":
            self.schema(
                schema.get("elementSchema"), owner, source.child("elementSchema"), depth + 1
            )
        elif kind == "Map":
            key, value = schema.get("mapKey"), schema.get("mapValue")
            if not isinstance(key, dict) or key.get("schema") != "string":
                self.issue("SCHEMA_SHAPE", "Map keys must have string schema.", owner, source)
            if not isinstance(value, dict):
                self.issue("SCHEMA_SHAPE", "Missing mapValue definition.", owner, source)
            else:
                self.schema(
                    value.get("schema"), owner, source.child("mapValue", "schema"), depth + 1
                )
        elif kind == "Object":
            fields = schema.get("fields")
            if not isinstance(fields, list):
                self.issue("SCHEMA_SHAPE", "Object fields must be an array.", owner, source)
                return
            names = set()
            for index, entry in enumerate(fields):
                location = source.child("fields", index)
                if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                    self.issue("SCHEMA_SHAPE", "Field requires a name.", owner, location)
                    continue
                if entry["name"] in names:
                    self.issue("SCHEMA_SHAPE", "Duplicate field name.", owner, location)
                names.add(entry["name"])
                self.schema(entry.get("schema"), owner, location.child("schema"), depth + 1)
        else:
            self.enum_schema(schema, owner, source)

    def enum_schema(self, schema: dict, owner: str, source: Source) -> None:
        primitive = schema.get("valueSchema")
        if primitive not in ("string", "integer"):
            self.issue(
                "SCHEMA_SHAPE",
                "Enum valueSchema must be string or integer.",
                owner,
                source.child("valueSchema"),
            )
            return
        entries = schema.get("enumValues", [])
        if not isinstance(entries, list):
            self.issue(
                "SCHEMA_SHAPE",
                "Enum enumValues must be an array when provided.",
                owner,
                source.child("enumValues"),
            )
            return
        names = set()
        values = set()
        for index, entry in enumerate(entries):
            location = source.child("enumValues", index)
            if not isinstance(entry, dict):
                self.issue("ENUM_VALUE", "Enum value must be an object.", owner, location)
                continue
            if "@type" in entry and types(entry) != {"EnumValue"}:
                self.issue(
                    "ENUM_VALUE",
                    "Enum entry type must be EnumValue when provided.",
                    owner,
                    location.child("@type"),
                )
            name = entry.get("name")
            if not valid_name(name):
                self.issue(
                    "ENUM_VALUE",
                    "Enum entry requires a valid programming name.",
                    owner,
                    location.child("name"),
                )
            elif name in names:
                self.issue(
                    "ENUM_VALUE", f"Duplicate enum name: {name}.", owner, location.child("name")
                )
            else:
                names.add(name)
            value = entry.get("enumValue")
            valid = (
                isinstance(value, str)
                if primitive == "string"
                else type(value) is int and -(2**31) <= value < 2**31
            )
            if not valid:
                self.issue(
                    "ENUM_VALUE",
                    f"Enum literal must match {primitive} valueSchema.",
                    owner,
                    location.child("enumValue"),
                )
            elif value in values:
                self.issue(
                    "ENUM_VALUE", "Enum literal must be unique.", owner, location.child("enumValue")
                )
            else:
                values.add(value)

    def content(self, declaration: Declaration) -> None:
        raw, owner, source = declaration.raw, declaration.owner, declaration.source
        if not valid_name(raw.get("name")):
            self.issue(
                "CONTENT_SHAPE",
                "Content requires a valid programming name.",
                owner,
                source.child("name"),
            )
        if "writable" in raw and type(raw["writable"]) is not bool:
            self.issue(
                "CONTENT_SHAPE", "writable must be a boolean.", owner, source.child("writable")
            )
        core = types(raw) & CONTENT_KINDS
        if len(core) != 1:
            self.issue("CONTENT_TYPE", "Expected one core content type.", owner, source)
            return
        kind = next(iter(core))
        if kind in {"Property", "Telemetry"}:
            self.schema(raw.get("schema"), owner, source.child("schema"))
        elif kind == "Component":
            target = raw.get("schema")
            if not isinstance(target, str) or target not in self.result.collection.models:
                self.issue("MISSING_COMPONENT", f"Unresolved component: {target}", owner, source)
            else:
                self.reference(owner, target, "component", source)
        elif kind == "Relationship":
            for field_name in ("minMultiplicity", "maxMultiplicity"):
                if field_name not in raw:
                    continue
                value = raw[field_name]
                valid = type(value) is int and (
                    value == 0 if field_name == "minMultiplicity" else 1 <= value < 2**31
                )
                if not valid:
                    bound = "0" if field_name == "minMultiplicity" else "a positive 32-bit integer"
                    self.issue(
                        "CONTENT_SHAPE",
                        f"{field_name} must be {bound}.",
                        owner,
                        source.child(field_name),
                    )
            if "target" in raw:
                target = raw["target"]
                if not isinstance(target, str) or len(target) > 2048 or not DTMI.fullmatch(target):
                    self.issue(
                        "CONTENT_SHAPE",
                        "Relationship target must be a valid DTMI.",
                        owner,
                        source.child("target"),
                    )
            properties = raw.get("properties", [])
            if not isinstance(properties, list):
                self.issue(
                    "CONTENT_SHAPE", "Relationship properties must be an array.", owner, source
                )
                return
            names = set()
            for index, entry in enumerate(properties):
                location = source.child("properties", index)
                if not isinstance(entry, dict):
                    self.issue("CONTENT_SHAPE", "Invalid relationship property.", owner, location)
                    continue
                if types(entry) & CONTENT_KINDS != {"Property"}:
                    self.issue(
                        "CONTENT_TYPE",
                        "Relationship state must contain only Properties.",
                        owner,
                        location.child("@type"),
                    )
                    continue
                name = entry.get("name")
                if isinstance(name, str):
                    if name in names:
                        self.issue(
                            "CONTENT_SHAPE",
                            "Duplicate relationship property name.",
                            owner,
                            location.child("name"),
                        )
                    names.add(name)
                self.content(Declaration(owner, entry, location))
        else:
            for name in ("request", "response"):
                parameter = raw.get(name)
                if parameter is not None:
                    if not isinstance(parameter, dict):
                        self.issue("CONTENT_SHAPE", f"Invalid command {name}.", owner, source)
                    else:
                        self.schema(parameter.get("schema"), owner, source.child(name, "schema"))

    def local_contents(self, model: Model) -> dict[str, Declaration]:
        result = {}
        contents = model.raw.get("contents", [])
        if not isinstance(contents, list):
            self.issue("CONTENT_SHAPE", "contents must be an array.", model.id, model.source)
            return result
        for index, raw in enumerate(contents):
            source = model.source.child("contents", index)
            if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
                self.issue("CONTENT_SHAPE", "Content requires a name.", model.id, source)
                continue
            declaration = Declaration(model.id, raw, source)
            if raw["name"] in result:
                self.issue("CONTENT_CONFLICT", "Duplicate local content name.", model.id, source)
            else:
                result[raw["name"]] = declaration
            self.content(declaration)
        return result

    def inheritance(self) -> None:
        visited: set[str] = set()
        active: list[str] = []

        def visit(identifier: str) -> None:
            if identifier in active:
                self.issue(
                    "INHERITANCE_CYCLE",
                    " -> ".join([*active, identifier]),
                    identifier,
                    self.result.collection.models[identifier].source,
                )
                return
            if identifier in visited:
                return
            model = self.result.collection.models[identifier]
            if len(active) >= 128:
                self.issue(
                    "RESOLUTION_LIMIT", "Inheritance exceeds 128 levels.", identifier, model.source
                )
                return
            active.append(identifier)
            local = self.result.contents[identifier]
            merged: dict[str, Declaration] = {}
            origins: dict[str, dict[Source, Declaration]] = {}

            def merge(name: str, declaration: Declaration) -> None:
                previous = merged.get(name)
                if previous and previous.raw != declaration.raw:
                    self.issue(
                        "CONTENT_CONFLICT",
                        f"Incompatible inherited/local {name}: "
                        f"{previous.source} and {declaration.source}.",
                        identifier,
                        declaration.source,
                    )
                    return
                origins.setdefault(name, {})[declaration.source] = declaration
                if previous is None or declaration.source < previous.source:
                    merged[name] = declaration

            for parent in self.result.parents.get(identifier, []):
                if parent not in self.result.collection.models:
                    self.issue(
                        "MISSING_PARENT", f"Unresolved parent: {parent}", identifier, model.source
                    )
                else:
                    visit(parent)
                    for name, declaration in self.result.contents[parent].items():
                        for origin in self.result.origins.get(parent, {}).get(name, [declaration]):
                            merge(name, origin)
            for name, declaration in local.items():
                merge(name, declaration)
            self.result.contents[identifier] = dict(sorted(merged.items()))
            self.result.origins[identifier] = {
                name: [entries[source] for source in sorted(entries)]
                for name, entries in sorted(origins.items())
            }
            active.pop()
            visited.add(identifier)

        for identifier in self.result.collection.models:
            visit(identifier)

    def extensions(self, model: Model) -> None:
        contexts = set(model.contexts)
        for context in sorted(contexts - EXTENSIONS - {"dtmi:dtdl:context;3"}):
            self.issue(
                "UNKNOWN_EXTENSION", f"Unsupported context: {context}", model.id, model.source
            )

        def inspect(raw: Any, source: Source) -> None:
            if isinstance(raw, dict):
                adjuncts = types(raw)
                known = (
                    CONTENT_KINDS
                    | SCHEMA_KINDS
                    | set(QUANTITY_UNITS)
                    | {
                        "Interface",
                        "Field",
                        "MapKey",
                        "MapValue",
                        "EnumValue",
                        "CommandRequest",
                        "CommandResponse",
                        "ValueAnnotation",
                        "Override",
                    }
                )
                for unknown in sorted(adjuncts - known):
                    self.issue("UNKNOWN_TYPE", f"Unsupported type: {unknown}", model.id, source)
                quantities = adjuncts & set(QUANTITY_UNITS)
                if quantities:
                    if QUANTITATIVE not in contexts:
                        self.issue(
                            "EXTENSION_CONTEXT",
                            "Quantity requires quantitativeTypes v1.",
                            model.id,
                            source,
                        )
                    if raw.get("schema") not in ("integer", "long", "float", "double"):
                        self.issue(
                            "QUANTITY_SCHEMA", "Quantity schema must be numeric.", model.id, source
                        )
                    if "unit" in raw and (
                        not isinstance(raw["unit"], str)
                        or any(
                            raw["unit"] not in UNIT_VALUES[QUANTITY_UNITS[q]] for q in quantities
                        )
                    ):
                        self.issue(
                            "QUANTITY_UNIT",
                            "Unit must be a supported quantity unit string.",
                            model.id,
                            source.child("unit"),
                        )
                if "ValueAnnotation" in adjuncts:
                    if ANNOTATION not in contexts or not adjuncts & {"Property", "Telemetry"}:
                        self.issue(
                            "EXTENSION_CONTEXT",
                            "Invalid annotation context/co-type.",
                            model.id,
                            source,
                        )
                    name = raw.get("annotates")
                    annotated = (
                        self.result.contents[model.id].get(name) if isinstance(name, str) else None
                    )
                    if annotated is None or not types(annotated.raw) & {"Property", "Telemetry"}:
                        self.issue(
                            "ANNOTATION_TARGET",
                            "annotates must reference a sibling value.",
                            model.id,
                            source,
                        )
                    if "Override" in adjuncts:
                        if OVERRIDING not in contexts:
                            self.issue(
                                "EXTENSION_CONTEXT",
                                "Override requires overriding v1.",
                                model.id,
                                source,
                            )
                        field_name = raw.get("overrides")
                        if field_name != "unit":
                            self.issue(
                                "OVERRIDE_FIELD",
                                "Only quantitative unit overrides supported.",
                                model.id,
                                source,
                            )
                        elif annotated:
                            targets = types(annotated.raw) & set(QUANTITY_UNITS)
                            if not targets or any(
                                raw.get("schema") != QUANTITY_UNITS[q] for q in targets
                            ):
                                self.issue(
                                    "OVERRIDE_SCHEMA",
                                    "Override unit schema does not match.",
                                    model.id,
                                    source,
                                )
                elif "Override" in adjuncts:
                    self.issue(
                        "OVERRIDE_ANNOTATION",
                        "Override requires ValueAnnotation.",
                        model.id,
                        source,
                    )
                for name, child in raw.items():
                    inspect(child, source.child(name))
            elif isinstance(raw, list):
                for index, child in enumerate(raw):
                    inspect(child, source.child(index))

        inspect(model.raw, model.source)

    def run(self) -> Resolution:
        models = [
            self.result.collection.models[identifier]
            for identifier in sorted(self.result.collection.models)
        ]
        for model in models:
            self.index_schema(model.raw, model.id, model.source)
        for model in models:
            parents = model.raw.get("extends", [])
            parents = [parents] if isinstance(parents, str) else parents
            if not isinstance(parents, list) or not all(isinstance(p, str) for p in parents):
                self.issue(
                    "PARENT_SHAPE", "extends must contain interface DTMIs.", model.id, model.source
                )
                parents = []
            self.result.parents[model.id] = sorted(set(parents))
            for parent in parents:
                self.reference(model.id, parent, "extends", model.source.child("extends"))
            self.result.contents[model.id] = self.local_contents(model)
            schemas = model.raw.get("schemas", [])
            if not isinstance(schemas, list):
                self.issue("SCHEMA_SHAPE", "schemas must be an array.", model.id, model.source)
                schemas = []
            for index, schema in enumerate(schemas):
                self.schema(schema, model.id, model.source.child("schemas", index))
        self.inheritance()
        for model in models:
            self.extensions(model)
        return self.result


def resolve(collection: Collection) -> Resolution:
    return Resolver(collection).run()
