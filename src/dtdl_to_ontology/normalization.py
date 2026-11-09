"""Normalize only explicitly specified DTDL representations, retaining pointers."""

import re
from typing import Any

from .extensions import (
    EXTENSION_ALIASES,
    extension_alias_is_active,
    extension_alias_metadata,
)
from .identifiers import valid_dtmi
from .model import Finding, Source
from .vocabulary import QUANTITY_UNITS, UNIT_VALUES

MATERIALS = {
    "Interface",
    "Property",
    "Telemetry",
    "Command",
    "Component",
    "Relationship",
    "Array",
    "Enum",
    "Map",
    "Object",
    "Field",
    "MapKey",
    "MapValue",
    "CommandRequest",
    "CommandResponse",
    "EnumValue",
}
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
MEMBERS = {
    "name",
    "schema",
    "contents",
    "extends",
    "schemas",
    "fields",
    "elementSchema",
    "mapKey",
    "mapValue",
    "enumValues",
    "valueSchema",
    "enumValue",
    "request",
    "response",
    "properties",
    "target",
    "comment",
    "description",
    "displayName",
    "writable",
    "minMultiplicity",
    "maxMultiplicity",
    "commandType",
}
SETS = {"contents", "extends", "schemas", "fields", "enumValues", "properties"}
ELEMENT_MEMBERS = SETS | {"schema", "elementSchema", "mapKey", "mapValue", "request", "response"}
INFERRED = {
    "fields": "Field",
    "mapKey": "MapKey",
    "mapValue": "MapValue",
    "request": "CommandRequest",
    "response": "CommandResponse",
    "enumValues": "EnumValue",
}
LANGUAGE = re.compile(r"[a-z]{2,4}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|[0-9]{3}))?\Z")


def term(value: str) -> str:
    for version in (2, 3):
        for kind, known in (
            (
                "class",
                MATERIALS | (QUANTITY_UNITS.keys() | UNIT_VALUES.keys() if version == 2 else set()),
            ),
            ("property", MEMBERS | ({"unit"} if version == 2 else set())),
            ("instance:Schema", PRIMITIVES),
            ("instance:CommandType", {"synchronous", "asynchronous"}),
        ):
            prefix = f"dtmi:dtdl:{kind}:"
            if value.startswith(prefix) and value.endswith(f";{version}"):
                name = value[len(prefix) : -(len(str(version)) + 1)]
                if name in known:
                    return name
    for unit_class, values in UNIT_VALUES.items():
        prefix = f"dtmi:dtdl:instance:{unit_class}:"
        if value.startswith(prefix) and value.endswith(";2") and value[len(prefix) : -2] in values:
            return value[len(prefix) : -2]
    if value in EXTENSION_ALIASES:
        return EXTENSION_ALIASES[value]
    match = re.fullmatch(r"dtmi:standard:schema:geospatial:(\w+);3", value)
    return match[1] if match else value


class Normalizer:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.contexts: dict[Source, tuple[str, ...]] = {}
        self.locations: dict[Source, Source] = {}
        self.changes: list[dict] = []
        self.sources: dict[int, Source] = {}
        self.originals: dict[int, dict] = {}
        self.members: dict[tuple[int, str], Source] = {}

    def issue(self, code: str, message: str, source: Source, owner: str | None) -> None:
        self.findings.append(Finding(code, message, source, owner))

    def normalized_term(
        self, value: str, contexts: tuple[str, ...], source: Source, owner: str | None
    ) -> str:
        normalized = term(value)
        if extension_alias_metadata(value) is not None and not extension_alias_is_active(
            value, contexts
        ):
            self.issue(
                "EXTENSION_CONTEXT",
                "Extension IRI does not match the active extension version.",
                source,
                owner,
            )
        canonical = re.fullmatch(
            r"dtmi:dtdl:(?:class|property|instance:Schema|instance:CommandType):\w+;([23])",
            value,
        )
        if canonical and f"dtmi:dtdl:context;{canonical[1]}" not in contexts:
            self.issue("TERM_VERSION", "Core IRI does not match the active context.", source, owner)
        return normalized

    def active_context(
        self, raw: dict, source: Source, parent: tuple[str, ...], owner: str | None
    ) -> tuple[str, ...]:
        values = raw.get("@context", [])
        values = [values] if isinstance(values, str) else values
        active = {value.partition(";")[0]: value for value in parent}
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            self.issue("CONTEXT", "Context must be a string or string array.", source, owner)
            return parent
        extension_seen = False
        for index, value in enumerate(values):
            location = (
                source.child("@context", index)
                if isinstance(raw.get("@context"), list)
                else source.child("@context")
            )
            if not valid_dtmi(value) or ";" not in value:
                self.issue("CONTEXT", "Context requires a versioned user DTMI.", location, owner)
                continue
            family = value.partition(";")[0]
            if family == "dtmi:dtdl:context":
                if extension_seen:
                    self.issue(
                        "CONTEXT_ORDER", "Core context must precede extensions.", location, owner
                    )
            else:
                extension_seen = True
            active[family] = value
        return tuple(active.values())

    def localized(self, value: Any, source: Source, owner: str | None) -> Any:
        if isinstance(value, str):
            entries = {"en": value}
        elif isinstance(value, dict):
            entries = value
        elif isinstance(value, list):
            entries = {}
            for index, item in enumerate(value):
                location = source.child(index)
                if isinstance(item, str):
                    language, text = "en", item
                elif isinstance(item, dict) and set(item) <= {"@value", "@language"}:
                    language, text = item.get("@language", "en"), item.get("@value")
                else:
                    self.issue(
                        "LOCALIZED_STRING", "Invalid language-tagged value.", location, owner
                    )
                    continue
                if not isinstance(language, str) or not LANGUAGE.fullmatch(language):
                    self.issue("LOCALIZED_STRING", "Invalid DTDL language tag.", location, owner)
                    continue
                if language in entries:
                    self.issue("LOCALIZED_STRING", "Duplicate language/default.", location, owner)
                entries[language] = text
        else:
            self.issue("LOCALIZED_STRING", "Expected a localizable string.", source, owner)
            return value
        for language, text in entries.items():
            if not LANGUAGE.fullmatch(language) or not isinstance(text, str) or len(text) > 512:
                self.issue(
                    "LOCALIZED_STRING",
                    "Invalid language tag or string (maximum 512).",
                    source,
                    owner,
                )
        if isinstance(value, str):
            return value
        return dict(sorted(entries.items()))

    def literal(self, value: Any, source: Source, owner: str | None) -> Any:
        if not isinstance(value, dict) or "@value" not in value:
            return value
        literal = value["@value"]
        expected = (
            "boolean"
            if type(literal) is bool
            else "integer"
            if type(literal) is int
            else "string"
            if isinstance(literal, str)
            else None
        )
        datatype = value.get("@type")
        if isinstance(datatype, list) and len(datatype) == 1:
            datatype = datatype[0]
        if (
            set(value) - {"@value", "@type"}
            or expected is None
            or (
                "@type" in value
                and (
                    not isinstance(datatype, str)
                    or datatype
                    not in {f"xsd:{expected}", f"http://www.w3.org/2001/XMLSchema#{expected}"}
                )
            )
        ):
            self.issue("LITERAL", "Invalid representational literal.", source, owner)
        return literal

    def element(
        self,
        raw: Any,
        source: Source,
        parent: tuple[str, ...] = (),
        owner: str | None = None,
        inferred: str | None = None,
    ) -> Any:
        if not isinstance(raw, dict):
            return self.normalized_term(raw, parent, source, owner) if isinstance(raw, str) else raw
        contexts = self.active_context(raw, source, parent, owner)
        core = next((v for v in contexts if v.startswith("dtmi:dtdl:context;")), "")
        identifier = raw.get("@id")
        raw_types = raw.get("@type", [])
        raw_types = [raw_types] if isinstance(raw_types, str) else raw_types
        normalized_types = (
            [
                self.normalized_term(v, contexts, source.child("@type"), owner)
                for v in raw_types
                if isinstance(v, str)
            ]
            if isinstance(raw_types, list)
            else []
        )
        if core == "dtmi:dtdl:context;2" and inferred in {"CommandRequest", "CommandResponse"}:
            normalized_types = [
                inferred if v in {"CommandPayload", "dtmi:dtdl:class:CommandPayload;2"} else v
                for v in normalized_types
            ]
        if "Interface" in normalized_types and isinstance(identifier, str):
            owner = identifier
        self.contexts[source] = contexts
        result = {}
        for key, value in raw.items():
            location = source.child(key)
            name = self.normalized_term(key, contexts, location, owner)
            self.locations[source.child(name)] = location
            if name in result:
                self.issue(
                    "MEMBER_ALIAS", f"Both spellings of {name} are present.", location, owner
                )
                continue
            if name in {"@context", "@id"}:
                result[name] = value
                continue
            if name == "@type":
                result[name] = (
                    normalized_types[0] if len(normalized_types) == 1 else normalized_types
                )
                if not isinstance(value, (str, list)) or (
                    isinstance(value, list) and not all(isinstance(v, str) for v in value)
                ):
                    self.issue(
                        "MATERIAL_TYPE", "@type must be a string or string array.", location, owner
                    )
                continue
            if name in {"description", "displayName"}:
                result[name] = self.localized(value, location, owner)
                continue
            if name in SETS:
                values = value if isinstance(value, list) else [value]
                result[name] = []
                for index, child in enumerate(values):
                    child_source = location.child(index) if isinstance(value, list) else location
                    normalized_source = source.child(name, index)
                    self.locations[normalized_source] = child_source
                    result[name].append(
                        self.element(child, child_source, contexts, owner, INFERRED.get(name))
                    )
                continue
            if isinstance(value, list):
                if len(value) > 1 or (
                    not value
                    and name
                    in {
                        "name",
                        "schema",
                        "elementSchema",
                        "mapKey",
                        "mapValue",
                        "valueSchema",
                        "enumValue",
                    }
                ):
                    self.issue(
                        "CARDINALITY", f"{name} requires a singleton value.", location, owner
                    )
                if not value:
                    continue
                location = location.child(0)
                self.locations[source.child(name)] = location
                value = value[0]
            if name in ELEMENT_MEMBERS:
                value = self.element(value, location, contexts, owner, INFERRED.get(name))
            else:
                if name != "target":
                    value = self.literal(value, location, owner)
                if isinstance(value, str) and name in {
                    "schema",
                    "valueSchema",
                    "commandType",
                    "unit",
                }:
                    value = self.normalized_term(value, contexts, location, owner)
            result[name] = value
        if "@type" not in raw and inferred:
            result["@type"] = inferred
        self.sources[id(result)] = source
        self.originals[id(result)] = raw
        for key in raw:
            self.members[(id(result), term(key))] = source.child(key)
        if raw != result:
            self.changes.append({"source": source, "owner": owner})
        return result
