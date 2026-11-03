"""Offline source interpretation for DTDL v3-compatible extensions.

This module validates source declarations and extracts their semantics. It
does not map extension behavior to an ontology or approve semantic loss.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .geo import GEO_ALIASES, GEOSCHEMAS
from .model import Finding, Source
from .vocabulary import (
    ANNOTATION,
    ANNOTATION_V2,
    EXTENSIONS,
    HISTORIZATION,
    HISTORIZATION_V2,
    MQTT_V1,
    MQTT_V2,
    MQTT_V3,
    OVERRIDING,
    OVERRIDING_V2,
    QUANTITATIVE,
    QUANTITY_UNITS,
    REQUIREMENT,
    UNIT_VALUES,
)

MQTT_V1_METAMODEL_SOURCE = (
    "https://github.com/Azure/opendigitaltwins-dtdl/blob/"
    "d19669a438a63be377c3cfc2fcabeac2e16ad55b/"
    "DTDL/v3/metamodel/DTDL.FeatureExtension.mqtt.v1.RDF-SHACL.json"
)
MQTT_V3_METAMODEL_SOURCE = (
    "https://github.com/Azure/opendigitaltwins-dtdl/blob/"
    "d19669a438a63be377c3cfc2fcabeac2e16ad55b/"
    "DTDL/v4/metamodel/DTDL.FeatureExtension.mqtt.v3.RDF-SHACL.json"
)

_CONTEXT_FAMILY = {
    ANNOTATION: ("annotation", 1),
    ANNOTATION_V2: ("annotation", 2),
    OVERRIDING: ("overriding", 1),
    OVERRIDING_V2: ("overriding", 2),
    HISTORIZATION: ("historization", 1),
    HISTORIZATION_V2: ("historization", 2),
    MQTT_V1: ("mqtt", 1),
    MQTT_V2: ("mqtt", 2),
    MQTT_V3: ("mqtt", 3),
    QUANTITATIVE: ("quantitativeTypes", 1),
    REQUIREMENT: ("requirement", 1),
}

_TYPE_CONTEXTS = {
    "Mqtt": "mqtt",
    "Idempotent": "mqtt",
    "Cacheable": "mqtt",
    "Transparent": "mqtt",
    "Indexed": "mqtt",
    "Result": "mqtt",
    "NormalResult": "mqtt",
    "ErrorResult": "mqtt",
    "Error": "mqtt",
    "ErrorMessage": "mqtt",
    "ValueAnnotation": "annotation",
    "Override": "overriding",
    "Historized": "historization",
    "Required": "requirement",
}
_EXTENSION_CLASS_NAMES = {
    "annotation": {1: ("ValueAnnotation",), 2: ("ValueAnnotation",)},
    "historization": {1: ("Historized",), 2: ("Historized",)},
    "mqtt": {
        1: ("Mqtt", "Idempotent", "Cacheable", "Indexed"),
        2: ("Mqtt", "Idempotent", "Cacheable", "Transparent", "Indexed"),
        3: (
            "Mqtt",
            "Idempotent",
            "Cacheable",
            "Transparent",
            "Indexed",
            "Result",
            "NormalResult",
            "ErrorResult",
            "Error",
            "ErrorMessage",
        ),
    },
    "overriding": {1: ("Override",), 2: ("Override",)},
    "quantitativeTypes": {
        1: tuple(QUANTITY_UNITS)
        + (
            "QuantitativeType",
            "RatioUnit",
            "UnitPrefix",
            "DecimalUnit",
            "BinaryUnit",
            "SymbolicUnit",
        )
    },
    "requirement": {1: ("Required",)},
}
QUANTITATIVE_UNIT_PREFIXES = (
    "deci",
    "centi",
    "milli",
    "micro",
    "nano",
    "pico",
    "femto",
    "atto",
    "zepto",
    "yocto",
    "deca",
    "hecto",
    "kilo",
    "mega",
    "giga",
    "tera",
    "peta",
    "exa",
    "zetta",
    "yotta",
    "kibi",
    "mebi",
    "gibi",
    "tebi",
    "pebi",
    "exbi",
    "zebi",
    "yobi",
)

# These identifiers mirror the @id entries in the pinned upstream context
# files. QuantitativeTypes alone uses a `class:` segment; other extensions
# identify adjunct types directly under their versioned namespace.
EXTENSION_TYPE_ALIASES: dict[str, tuple[str, str, int]] = {}
for _family, _versions in _EXTENSION_CLASS_NAMES.items():
    for _version, _names in _versions.items():
        for _name in _names:
            _path = f"class:{_name}" if _family == "quantitativeTypes" else _name
            _iri = f"dtmi:dtdl:extension:{_family}:v{_version}:{_path}"
            EXTENSION_TYPE_ALIASES[_iri] = (_name, _family, _version)

QUANTITATIVE_ENUM_ALIASES = {
    f"dtmi:dtdl:extension:quantitativeTypes:v1:enum:{name}": name
    for name in set(UNIT_VALUES) | {"DecimalPrefix", "BinaryPrefix"}
}
for _iri, _name in QUANTITATIVE_ENUM_ALIASES.items():
    EXTENSION_TYPE_ALIASES[_iri] = (_name, "quantitativeTypes", 1)

_CONTEXT_TYPE_ALIASES = {alias: metadata[0] for alias, metadata in EXTENSION_TYPE_ALIASES.items()}
QUANTITATIVE_INSTANCE_ALIASES = {
    f"dtmi:dtdl:extension:quantitativeTypes:v1:unit:{value}": value
    for value in {unit for values in UNIT_VALUES.values() for unit in values}
}
QUANTITATIVE_INSTANCE_ALIASES.update(
    {
        f"dtmi:dtdl:extension:quantitativeTypes:v1:unitprefix:{value}": value
        for value in QUANTITATIVE_UNIT_PREFIXES
    }
)
QUANTITATIVE_SCHEMA_ALIASES = dict(QUANTITATIVE_ENUM_ALIASES)
EXTENSION_MEMBER_ALIASES = {
    **{
        f"dtmi:dtdl:extension:annotation:v{version}:ValueAnnotation:annotates": "annotates"
        for version in (1, 2)
    },
    **{
        f"dtmi:dtdl:extension:overriding:v{version}:Override:overrides": "overrides"
        for version in (1, 2)
    },
    **{
        f"dtmi:dtdl:extension:mqtt:v{version}:{parent}:{member}": member
        for version, parent, members in (
            (1, "Mqtt", ("commandTopic", "telemetryTopic", "payloadFormat")),
            (1, "Cacheable", ("ttl",)),
            (1, "Indexed", ("index",)),
            (
                2,
                "Mqtt",
                (
                    "commandTopic",
                    "telemetryTopic",
                    "payloadFormat",
                    "cmdServiceGroupId",
                    "telemServiceGroupId",
                ),
            ),
            (2, "Cacheable", ("ttl",)),
            (2, "Indexed", ("index",)),
            (2, "Transparent", ()),
            (
                3,
                "Mqtt",
                (
                    "commandTopic",
                    "telemetryTopic",
                    "payloadFormat",
                    "cmdServiceGroupId",
                    "telemServiceGroupId",
                ),
            ),
            (3, "Cacheable", ("ttl",)),
            (3, "Indexed", ("index",)),
            (3, "Transparent", ()),
        )
        for member in members
    },
}
EXTENSION_ALIASES = {
    **_CONTEXT_TYPE_ALIASES,
    **QUANTITATIVE_ENUM_ALIASES,
    **QUANTITATIVE_INSTANCE_ALIASES,
    **QUANTITATIVE_SCHEMA_ALIASES,
    **EXTENSION_MEMBER_ALIASES,
    "dtmi:dtdl:extension:quantitativeTypes:v1:property:unit": "unit",
}

EXTENSION_PROPERTY_ALIASES: dict[str, tuple[str, str, int | None]] = {
    "unit": ("unit", "quantitativeTypes", None),
    "dtmi:dtdl:extension:quantitativeTypes:v1:property:unit": ("unit", "quantitativeTypes", 1),
}
for _mqtt_version in (1, 2, 3):
    _compact = "index"
    _canonical = f"dtmi:dtdl:extension:mqtt:v{_mqtt_version}:Indexed:index"
    EXTENSION_PROPERTY_ALIASES.setdefault(_compact, (_compact, "mqtt", None))
    EXTENSION_PROPERTY_ALIASES[_canonical] = (_compact, "mqtt", _mqtt_version)

_CANONICAL_MEMBER_METADATA = {
    alias: (term, family, version)
    for family, versions in _EXTENSION_CLASS_NAMES.items()
    for version in versions
    for alias, term in EXTENSION_MEMBER_ALIASES.items()
    if alias.startswith(f"dtmi:dtdl:extension:{family}:v{version}:")
}
EXTENSION_ALIAS_METADATA: dict[str, tuple[str, str, int]] = {
    **EXTENSION_TYPE_ALIASES,
    **_CANONICAL_MEMBER_METADATA,
    **{
        alias: (term, "quantitativeTypes", 1)
        for alias, term in QUANTITATIVE_INSTANCE_ALIASES.items()
    },
    **{
        alias: (term, family, version)
        for alias, (term, family, version) in EXTENSION_PROPERTY_ALIASES.items()
        if version is not None
    },
}

# Exported for the core static member validator. Each adjunct only authorizes
# its own extension-defined members; validation below checks version and use.
EXTENSION_MEMBERS = {
    "Mqtt": {
        "commandTopic",
        "payloadFormat",
        "telemetryTopic",
        "cmdServiceGroupId",
        "telemServiceGroupId",
    },
    "Cacheable": {"ttl"},
    "Indexed": {"index"},
    "ValueAnnotation": {"annotates"},
    "Override": {"overrides"},
}
EXTENSION_TYPES = frozenset(_TYPE_CONTEXTS)

_MATERIAL_TYPES = {
    "Mqtt": {"Interface"},
    "Idempotent": {"Command"},
    "Cacheable": {"Command"},
    "Transparent": {"CommandRequest", "CommandResponse"},
    "Indexed": {"EnumValue", "Field", "Telemetry"},
    "Result": {"Object"},
    "NormalResult": {"Field"},
    "ErrorResult": {"Field"},
    "Error": {"Object"},
    "ErrorMessage": {"Field"},
    "ValueAnnotation": {"Property", "Telemetry"},
    "Override": {"Property"},
    "Historized": {"Property", "Telemetry"},
    "Required": {"Field"},
}

_MQTT_FIELDS = {
    "commandTopic": (1, "topic"),
    "payloadFormat": (1, "string"),
    "telemetryTopic": (1, "topic"),
    "cmdServiceGroupId": (2, "service-group"),
    "telemServiceGroupId": (2, "service-group"),
}
_PROPERTY_OWNERS = {
    "commandTopic": "Mqtt",
    "payloadFormat": "Mqtt",
    "telemetryTopic": "Mqtt",
    "cmdServiceGroupId": "Mqtt",
    "telemServiceGroupId": "Mqtt",
    "ttl": "Cacheable",
    "index": "Indexed",
    "annotates": "ValueAnnotation",
    "overrides": "Override",
}

_TOKEN = re.compile(r"^(?:[A-Za-z]+:)?[A-Za-z]+$")
_DURATION = re.compile(
    r"^P(?:\d+(?:[.,]\d+)?W|(?=\d|T)(?:\d+(?:[.,]\d+)?Y)?"
    r"(?:\d+(?:[.,]\d+)?M)?(?:\d+(?:[.,]\d+)?D)?"
    r"(?:T(?=\d)(?:\d+(?:[.,]\d+)?H)?(?:\d+(?:[.,]\d+)?M)?"
    r"(?:\d+(?:[.,]\d+)?S)?)?)$"
)


def _types(raw: Any) -> set[str]:
    if not isinstance(raw, Mapping):
        return set()
    value = raw.get("@type", ())
    values = value if isinstance(value, list) else [value]
    return {EXTENSION_ALIASES.get(item, item) for item in values if isinstance(item, str)}


def _contexts(contexts: Sequence[str]) -> tuple[dict[str, int], list[str]]:
    versions: dict[str, int] = {}
    unknown: list[str] = []
    for context in contexts:
        family_version = _CONTEXT_FAMILY.get(context)
        if family_version:
            family, version = family_version
            versions[family] = max(version, versions.get(family, 0))
        elif context not in EXTENSIONS and context != "dtmi:dtdl:context;3":
            unknown.append(context)
    return versions, unknown


def extension_alias_metadata(value: str) -> tuple[str, str, int] | None:
    """Return exact alias metadata as (term, family, defining version)."""
    return EXTENSION_ALIAS_METADATA.get(value)


def extension_alias_is_active(value: str, contexts: Sequence[str]) -> bool | None:
    """Return whether a known canonical alias matches its active context version.

    ``None`` means the value is not one of the pinned canonical aliases. Core
    normalization should preserve such values for ordinary unknown-term
    validation rather than infer an extension meaning.
    """
    metadata = extension_alias_metadata(value)
    if metadata is None:
        return None
    _term, family, version = metadata
    active_versions, _unknown_contexts = _contexts(contexts)
    return active_versions.get(family) == version


def _source(source: Source, *parts: str | int) -> Source:
    return source.child(*parts)


def _finding(
    code: str,
    message: str,
    source: Source,
    owner: str,
) -> Finding:
    return Finding(code, message, source, owner)


def _is_topic(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    labels = value.split("/")
    if not labels or labels[0].startswith("$"):
        return False
    for label in labels:
        if label.startswith("{") and label.endswith("}"):
            if not _TOKEN.fullmatch(label[1:-1]):
                return False
        elif (
            not label
            or any(ord(char) < 0x21 or ord(char) > 0x7E for char in label)
            or any(char in '"+#{}/' for char in label)
        ):
            return False
    return True


def _is_service_group(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and all(0x21 <= ord(char) <= 0x7E and char not in '" +#{}/' for char in value)
    )


def _schema(raw: Any) -> Any:
    return raw.get("schema") if isinstance(raw, Mapping) else None


def _schema_type(schema: Any) -> str | None:
    if isinstance(schema, str):
        if schema.startswith("dtmi:dtdl:instance:Schema:"):
            return schema.rsplit(":", 1)[-1].split(";", 1)[0]
        return schema
    if isinstance(schema, Mapping):
        value = schema.get("@type")
        return value if isinstance(value, str) else None
    return None


def _in_collection(items: Any, adjunct: str) -> list[Mapping[str, Any]]:
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping) and adjunct in _types(item)]


def _validate_object_children(
    raw: Mapping[str, Any],
    types: set[str],
    source: Source,
    owner: str,
    findings: list[Finding],
) -> None:
    # These shapes mirror the pinned MQTT v3 RDF-SHACL constraints. The file
    # lives under DTDL/v4 but its sh:or explicitly accepts DTDL v3 classes.
    fields = raw.get("fields")
    if not isinstance(fields, list):
        return
    result = "Result" in types
    error = "Error" in types
    normal = _in_collection(fields, "NormalResult")
    exceptional = _in_collection(fields, "ErrorResult")
    messages = _in_collection(fields, "ErrorMessage")
    if result:
        for index, field in enumerate(fields):
            if not isinstance(field, Mapping):
                continue
            field_types = _types(field)
            if not ({"NormalResult", "ErrorResult"} & field_types):
                findings.append(
                    _finding(
                        "EXTENSION_SHAPE",
                        "Every field of a Result Object must be NormalResult or ErrorResult.",
                        _source(source, "fields", index, "@type"),
                        owner,
                    )
                )
        if len(normal) > 1:
            findings.append(
                _finding(
                    "EXTENSION_CARDINALITY",
                    "A Result Object may contain at most one NormalResult field.",
                    _source(source, "fields"),
                    owner,
                )
            )
        if len(exceptional) > 1:
            findings.append(
                _finding(
                    "EXTENSION_CARDINALITY",
                    "A Result Object may contain at most one ErrorResult field.",
                    _source(source, "fields"),
                    owner,
                )
            )
        for index, field in enumerate(fields):
            if (
                isinstance(field, Mapping)
                and ({"NormalResult", "ErrorResult"} & _types(field))
                and "Required" in _types(field)
            ):
                findings.append(
                    _finding(
                        "EXTENSION_CONFLICT",
                        "NormalResult and ErrorResult fields cannot be co-typed Required.",
                        _source(source, "fields", index, "@type"),
                        owner,
                    )
                )
    if error and len(messages) > 1:
        findings.append(
            _finding(
                "EXTENSION_CARDINALITY",
                "An Error Object may contain at most one ErrorMessage field.",
                _source(source, "fields"),
                owner,
            )
        )
    for index, field in enumerate(fields):
        if not isinstance(field, Mapping):
            continue
        field_types = _types(field)
        field_source = _source(source, "fields", index)
        if "NormalResult" in field_types or "ErrorResult" in field_types:
            if not result:
                findings.append(
                    _finding(
                        "EXTENSION_POSITION",
                        "NormalResult and ErrorResult fields must be within a Result Object.",
                        _source(field_source, "@type"),
                        owner,
                    )
                )
        if "ErrorMessage" in field_types:
            if not error:
                findings.append(
                    _finding(
                        "EXTENSION_POSITION",
                        "ErrorMessage fields must be within an Error Object.",
                        _source(field_source, "@type"),
                        owner,
                    )
                )
            if _schema_type(_schema(field)) != "string":
                findings.append(
                    _finding(
                        "EXTENSION_SCHEMA",
                        "An ErrorMessage field must have a string schema.",
                        _source(field_source, "schema"),
                        owner,
                    )
                )
        if "ErrorResult" in field_types:
            schema = _schema(field)
            primitive_schemas = {
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
            known_non_object = isinstance(schema, str) and (
                schema in primitive_schemas or schema.startswith("dtmi:dtdl:instance:Schema:")
            )
            if known_non_object or (
                isinstance(schema, Mapping)
                and ("Object" not in _types(schema) or "Error" not in _types(schema))
            ):
                findings.append(
                    _finding(
                        "EXTENSION_SCHEMA",
                        "An inline ErrorResult schema must be an Object co-typed Error.",
                        _source(field_source, "schema"),
                        owner,
                    )
                )


def _validate_indices(
    items: Any,
    source: Source,
    owner: str,
    findings: list[Finding],
) -> None:
    if not isinstance(items, list):
        return
    seen: dict[int, int] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping) or "Indexed" not in _types(item):
            continue
        value = item.get("index")
        item_source = _source(source, index)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            findings.append(
                _finding(
                    "EXTENSION_VALUE",
                    "An Indexed adjunct requires an integer index of at least 1.",
                    _source(item_source, "index"),
                    owner,
                )
            )
        elif value in seen:
            findings.append(
                _finding(
                    "EXTENSION_DUPLICATE",
                    f"Index {value} duplicates the index of another sibling.",
                    _source(item_source, "index"),
                    owner,
                )
            )
        else:
            seen[value] = index


def _override_property_schema(
    target: Mapping[str, Any],
    member: str,
    versions: dict[str, int],
) -> str | None:
    if member == "unit" and versions.get("quantitativeTypes") == 1:
        target_types = _types(target)
        unit_classes = {QUANTITY_UNITS[name] for name in target_types if name in QUANTITY_UNITS}
        return next(iter(unit_classes)) if len(unit_classes) == 1 else None
    if (
        member == "index"
        and versions.get("mqtt", 0)
        and "Indexed" in _types(target)
        and "Telemetry" in _types(target)
    ):
        return "integer"
    if (
        member == "annotates"
        and versions.get("annotation", 0)
        and "ValueAnnotation" in _types(target)
    ):
        return "string"
    if member == "overrides" and versions.get("overriding", 0) and "Override" in _types(target):
        return "string"
    return None


def _same_schema(actual: Any, expected: str) -> bool:
    allowed = {expected}
    if expected in UNIT_VALUES:
        allowed.add(f"dtmi:dtdl:extension:quantitativeTypes:v1:enum:{expected}")
    elif expected in {
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
    }:
        allowed.add(f"dtmi:dtdl:instance:Schema:{expected};3")
    return isinstance(actual, str) and actual in allowed


def validate(
    raw: dict,
    contexts: tuple[str, ...],
    source: Source,
    owner: str,
    siblings: dict[str, dict],
) -> list[Finding]:
    """Validate extension adjuncts and properties on one normalized element."""
    findings: list[Finding] = []
    versions, _unknown_contexts = _contexts(contexts)
    types = _types(raw)
    active_context_families = set(versions)
    raw_declared_types = raw.get("@type", ())
    declared_types = (
        raw_declared_types if isinstance(raw_declared_types, list) else [raw_declared_types]
    )
    for type_index, declared_type in enumerate(declared_types):
        metadata = (
            EXTENSION_TYPE_ALIASES.get(declared_type) if isinstance(declared_type, str) else None
        )
        if metadata is None:
            continue
        _term, family, version = metadata
        type_source = (
            _source(source, "@type", type_index)
            if isinstance(raw_declared_types, list)
            else _source(source, "@type")
        )
        if family not in versions:
            findings.append(
                _finding(
                    "EXTENSION_CONTEXT",
                    f"{declared_type} requires the {family} v{version} context.",
                    type_source,
                    owner,
                )
            )
        elif versions[family] != version:
            findings.append(
                _finding(
                    "EXTENSION_VERSION",
                    f"{declared_type} does not match the active "
                    f"{family} v{versions[family]} context.",
                    type_source,
                    owner,
                )
            )

    families = [family for family in _CONTEXT_FAMILY.values()]
    for family in {item[0] for item in families}:
        present = [c for c in contexts if _CONTEXT_FAMILY.get(c, (None,))[0] == family]
        if len(present) > 1:
            findings.append(
                _finding(
                    "EXTENSION_VERSION",
                    f"Only one {family} extension context version may be active.",
                    _source(source, "@context"),
                    owner,
                )
            )

    for adjunct, family in _TYPE_CONTEXTS.items():
        if adjunct not in types:
            continue
        if family not in active_context_families:
            findings.append(
                _finding(
                    "EXTENSION_CONTEXT",
                    f"{adjunct} requires the {family} extension context.",
                    _source(source, "@type"),
                    owner,
                )
            )
        material_types = _MATERIAL_TYPES[adjunct]
        if not (types & material_types):
            expected = " or ".join(sorted(material_types))
            findings.append(
                _finding(
                    "EXTENSION_TYPE",
                    f"{adjunct} requires an explicit material type of {expected}.",
                    _source(source, "@type"),
                    owner,
                )
            )
        if family == "mqtt":
            minimum_version = (
                2
                if adjunct == "Transparent"
                else (
                    3
                    if adjunct in {"Result", "NormalResult", "ErrorResult", "Error", "ErrorMessage"}
                    else 1
                )
            )
            if versions.get("mqtt", 0) < minimum_version:
                findings.append(
                    _finding(
                        "EXTENSION_VERSION",
                        f"{adjunct} requires MQTT extension version {minimum_version} or later.",
                        _source(source, "@type"),
                        owner,
                    )
                )

    if "Override" in types and "annotation" not in active_context_families:
        findings.append(
            _finding(
                "EXTENSION_CONTEXT",
                "Override requires an active Annotation context.",
                _source(source, "@context"),
                owner,
            )
        )
    if "Override" in types and "ValueAnnotation" not in types:
        findings.append(
            _finding(
                "EXTENSION_TYPE",
                "Override must be co-typed with ValueAnnotation.",
                _source(source, "@type"),
                owner,
            )
        )

    for member, adjunct in _PROPERTY_OWNERS.items():
        if member not in raw:
            continue
        family = _TYPE_CONTEXTS[adjunct]
        if family not in active_context_families or adjunct not in types:
            findings.append(
                _finding(
                    "EXTENSION_PROPERTY",
                    f"{member} is only valid with the {adjunct} adjunct and its context.",
                    _source(source, member),
                    owner,
                )
            )
    if "Mqtt" in types:
        if "payloadFormat" not in raw:
            findings.append(
                _finding(
                    "EXTENSION_REQUIRED",
                    "Mqtt requires payloadFormat.",
                    _source(source, "payloadFormat"),
                    owner,
                )
            )
        for member, (minimum_version, kind) in _MQTT_FIELDS.items():
            if member not in raw:
                continue
            if versions.get("mqtt", 0) < minimum_version:
                findings.append(
                    _finding(
                        "EXTENSION_VERSION",
                        f"{member} requires MQTT extension version {minimum_version} or later.",
                        _source(source, member),
                        owner,
                    )
                )
            value = raw[member]
            valid = (
                isinstance(value, str)
                if kind == "string"
                else _is_topic(value)
                if kind == "topic"
                else _is_service_group(value)
            )
            if not valid:
                description = (
                    "a valid MQTT topic pattern"
                    if kind == "topic"
                    else (
                        "a non-empty printable service group ID"
                        if kind == "service-group"
                        else "a string"
                    )
                )
                findings.append(
                    _finding(
                        "EXTENSION_VALUE",
                        f"{member} must be {description}.",
                        _source(source, member),
                        owner,
                    )
                )
    if "Cacheable" in types:
        if "Idempotent" not in types:
            findings.append(
                _finding(
                    "EXTENSION_CONFLICT",
                    "Cacheable requires the Command to also be co-typed Idempotent.",
                    _source(source, "@type"),
                    owner,
                )
            )
        ttl = raw.get("ttl")
        if "ttl" not in raw:
            findings.append(
                _finding(
                    "EXTENSION_REQUIRED",
                    "Cacheable requires ttl.",
                    _source(source, "ttl"),
                    owner,
                )
            )
        elif not isinstance(ttl, str) or not _DURATION.fullmatch(ttl):
            findings.append(
                _finding(
                    "EXTENSION_VALUE",
                    "ttl must be an ISO 8601 duration.",
                    _source(source, "ttl"),
                    owner,
                )
            )
    if "Indexed" in types and "index" not in raw:
        findings.append(
            _finding(
                "EXTENSION_REQUIRED",
                "Indexed requires index.",
                _source(source, "index"),
                owner,
            )
        )

    if "Transparent" in types:
        schema = _schema(raw)
        primitive_schemas = {
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
        is_primitive = isinstance(schema, str) and (
            schema in primitive_schemas or schema.startswith("dtmi:dtdl:instance:Schema:")
        )
        if (
            (isinstance(schema, Mapping) and "Object" not in _types(schema))
            or is_primitive
            or schema is None
        ):
            findings.append(
                _finding(
                    "EXTENSION_SCHEMA",
                    "Transparent requires an Object schema.",
                    _source(source, "schema"),
                    owner,
                )
            )
    if "ValueAnnotation" in types:
        annotated = raw.get("annotates")
        if not isinstance(annotated, str) or not annotated:
            findings.append(
                _finding(
                    "EXTENSION_REQUIRED",
                    "ValueAnnotation requires a non-empty annotates name.",
                    _source(source, "annotates"),
                    owner,
                )
            )
        elif annotated not in siblings:
            findings.append(
                _finding(
                    "EXTENSION_REFERENCE",
                    f"annotates must name an effective sibling; {annotated!r} was not found.",
                    _source(source, "annotates"),
                    owner,
                )
            )
        else:
            target_types = _types(siblings[annotated])
            if not (target_types & {"Property", "Telemetry"}):
                findings.append(
                    _finding(
                        "EXTENSION_REFERENCE",
                        "annotates must identify a Property or Telemetry sibling.",
                        _source(source, "annotates"),
                        owner,
                    )
                )
    if "Override" in types:
        member = raw.get("overrides")
        target_name = raw.get("annotates")
        target = siblings.get(target_name) if isinstance(target_name, str) else None
        if not isinstance(member, str) or not member:
            findings.append(
                _finding(
                    "EXTENSION_REQUIRED",
                    "Override requires an overrides IRI.",
                    _source(source, "overrides"),
                    owner,
                )
            )
        else:
            property_alias = EXTENSION_PROPERTY_ALIASES.get(member)
            normalized_member = property_alias[0] if property_alias else None
            property_family = property_alias[1] if property_alias else None
            property_version = property_alias[2] if property_alias else None
            if property_version is None and property_family:
                property_version = versions.get(property_family)
            if property_alias and property_version != versions.get(property_family):
                findings.append(
                    _finding(
                        "EXTENSION_VERSION",
                        "The overridden property IRI must name the active extension version.",
                        _source(source, "overrides"),
                        owner,
                    )
                )
            elif property_alias and property_family not in versions:
                findings.append(
                    _finding(
                        "EXTENSION_CONTEXT",
                        "The overridden property requires its defining extension context.",
                        _source(source, "overrides"),
                        owner,
                    )
                )
            expected = (
                _override_property_schema(target, normalized_member, versions)
                if isinstance(target, Mapping)
                and normalized_member is not None
                and property_alias is not None
                and property_version == versions.get(property_family)
                else None
            )
            if expected is None:
                findings.append(
                    _finding(
                        "EXTENSION_REFERENCE",
                        "overrides must identify a known extension property "
                        "on the annotated sibling, "
                        "defined by an active DTDLv3-compatible extension.",
                        _source(source, "overrides"),
                        owner,
                    )
                )
            elif not _same_schema(_schema(raw), expected):
                findings.append(
                    _finding(
                        "EXTENSION_SCHEMA",
                        f"The Override Property schema must match {expected}.",
                        _source(source, "schema"),
                        owner,
                    )
                )

    if "Indexed" in types:
        value = raw.get("index")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            if "index" in raw:
                findings.append(
                    _finding(
                        "EXTENSION_VALUE",
                        "An Indexed adjunct requires an integer index of at least 1.",
                        _source(source, "index"),
                        owner,
                    )
                )
    if (
        "Indexed" in types
        and isinstance(raw.get("index"), int)
        and not isinstance(raw.get("index"), bool)
    ):
        same_kind = "Telemetry" in types
        if same_kind:
            for sibling in siblings.values():
                if sibling is raw or sibling.get("name") == raw.get("name"):
                    continue
                if "Indexed" in _types(sibling) and "Telemetry" in _types(sibling):
                    if sibling.get("index") == raw.get("index"):
                        findings.append(
                            _finding(
                                "EXTENSION_DUPLICATE",
                                f"Index {raw['index']} duplicates another Telemetry sibling.",
                                _source(source, "index"),
                                owner,
                            )
                        )

    if "Object" in types and isinstance(raw.get("fields"), list):
        _validate_indices(raw["fields"], _source(source, "fields"), owner, findings)
    if "Enum" in types and isinstance(raw.get("enumValues"), list):
        _validate_indices(raw["enumValues"], _source(source, "enumValues"), owner, findings)
    if "Object" in types and isinstance(raw.get("fields"), list):
        _validate_object_children(raw, types, source, owner, findings)
    return findings


def semantics(raw: Any, contexts: tuple[str, ...]) -> dict[str, Any]:
    """Return structured source provenance for extensions and geo schemas."""
    versions, _unknown = _contexts(contexts)
    if isinstance(raw, str):
        geo_name = GEO_ALIASES.get(raw, raw if raw in GEOSCHEMAS else None)
        if geo_name:
            return {"geospatial": dict(GEOSCHEMAS[geo_name])}
        return {}
    if not isinstance(raw, Mapping):
        return {}

    result: dict[str, Any] = {}
    types = _types(raw)
    mqtt_types = sorted(
        types
        & {
            "Mqtt",
            "Idempotent",
            "Cacheable",
            "Transparent",
            "Indexed",
            "Result",
            "NormalResult",
            "ErrorResult",
            "Error",
            "ErrorMessage",
        }
    )
    if mqtt_types or any(key in raw for key in EXTENSION_MEMBERS["Mqtt"]):
        mqtt: dict[str, Any] = {
            "version": versions.get("mqtt"),
            "types": mqtt_types,
        }
        properties = {
            key: raw[key]
            for key in (
                "commandTopic",
                "telemetryTopic",
                "payloadFormat",
                "cmdServiceGroupId",
                "telemServiceGroupId",
                "ttl",
                "index",
            )
            if key in raw
        }
        if properties:
            mqtt["properties"] = properties
        if "Idempotent" in types:
            mqtt["idempotent"] = {"repeat_execution_permitted": True}
        if "Cacheable" in types:
            mqtt["cache"] = {"ttl": raw.get("ttl")}
        if "Transparent" in types:
            mqtt["wireEnvelope"] = {
                "omit_outer_command_request_or_response": True,
                "schema": raw.get("schema"),
            }
        if "Indexed" in types:
            mqtt["serializationIndex"] = raw.get("index")
        if "Result" in types:
            fields = raw.get("fields", [])
            mqtt["result"] = {
                "normal": [
                    {"name": field.get("name"), "schema": field.get("schema")}
                    for field in fields
                    if isinstance(field, Mapping) and "NormalResult" in _types(field)
                ],
                "errors": [
                    {"name": field.get("name"), "schema": field.get("schema")}
                    for field in fields
                    if isinstance(field, Mapping) and "ErrorResult" in _types(field)
                ],
                "mutually_exclusive": True,
            }
        if "Error" in types:
            fields = raw.get("fields", [])
            mqtt["error"] = {
                "messageFields": [
                    field.get("name")
                    for field in fields
                    if isinstance(field, Mapping) and "ErrorMessage" in _types(field)
                ]
            }
        result["mqtt"] = mqtt
    if "ValueAnnotation" in types or "Override" in types:
        result["annotation"] = {
            "version": versions.get("annotation"),
            "annotates": raw.get("annotates"),
            "override": raw.get("overrides") if "Override" in types else None,
        }
    if "Historized" in types:
        result["historization"] = {
            "version": versions.get("historization"),
            "historized": True,
            "intent": "retain value changes and change times",
        }
    if "Field" in types:
        result["presence"] = {
            "required": "Required" in types,
            "default": "optional",
            "enforced_by_source_contract": "Required" in types,
        }

    schema = raw.get("schema")
    if isinstance(schema, str):
        geo_name = GEO_ALIASES.get(schema, schema if schema in GEOSCHEMAS else None)
        if geo_name:
            result["geospatial"] = dict(GEOSCHEMAS[geo_name])
    return result
