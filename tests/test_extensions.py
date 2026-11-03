import json
from pathlib import Path

import pytest

from dtdl_to_ontology.extensions import (
    EXTENSION_ALIAS_METADATA,
    EXTENSION_ALIASES,
    EXTENSION_MEMBERS,
    EXTENSION_PROPERTY_ALIASES,
    EXTENSION_TYPE_ALIASES,
    EXTENSION_TYPES,
    MQTT_V1_METAMODEL_SOURCE,
    MQTT_V3_METAMODEL_SOURCE,
    QUANTITATIVE_INSTANCE_ALIASES,
    extension_alias_is_active,
    extension_alias_metadata,
    semantics,
    validate,
)
from dtdl_to_ontology.geo import GEO_ALIASES, GEOSCHEMAS
from dtdl_to_ontology.model import Source
from dtdl_to_ontology.vocabulary import (
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
    REQUIREMENT,
)

FIXTURE = Path(__file__).parent / "fixtures" / "extensions" / "valid.json"
OWNER = "dtmi:example:Test;1"


def types(*values):
    return {"@type": list(values)}


def run(raw, contexts, siblings=None, pointer="/element"):
    return validate(
        raw,
        tuple(contexts),
        Source("extensions.json", pointer),
        OWNER,
        siblings or {},
    )


def _walk_model(model):
    contexts = (
        tuple(model.get("@context", ()))
        if isinstance(model.get("@context"), list)
        else ((model["@context"],) if isinstance(model.get("@context"), str) else ())
    )
    contents = {
        item["name"]: item
        for item in model.get("contents", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    def walk(element, pointer):
        if not isinstance(element, dict):
            return
        yield element, contexts, pointer, contents
        for collection in ("contents", "schemas", "fields", "enumValues"):
            items = element.get(collection)
            if isinstance(items, list):
                for index, item in enumerate(items):
                    yield from walk(item, f"{pointer}/{collection}/{index}")
        for member in ("request", "response"):
            item = element.get(member)
            if isinstance(item, dict):
                yield from walk(item, f"{pointer}/{member}")
        if "schema" in element:
            yield from walk(element["schema"], f"{pointer}/schema")

    yield from walk(model, "/" + model.get("@id", "model"))


def test_versioned_extension_contexts_and_static_validator_exports():
    assert {
        ANNOTATION_V2,
        OVERRIDING_V2,
        HISTORIZATION,
        HISTORIZATION_V2,
        REQUIREMENT,
        MQTT_V1,
        MQTT_V2,
        MQTT_V3,
    } <= EXTENSIONS
    assert {"Mqtt", "Cacheable", "Indexed", "ValueAnnotation", "Override"} <= set(EXTENSION_MEMBERS)
    assert {
        "Mqtt",
        "Transparent",
        "Result",
        "Historized",
        "Required",
    } <= EXTENSION_TYPES
    assert (
        EXTENSION_ALIASES["dtmi:dtdl:extension:quantitativeTypes:v1:class:Temperature"]
        == "Temperature"
    )
    assert (
        QUANTITATIVE_INSTANCE_ALIASES["dtmi:dtdl:extension:quantitativeTypes:v1:unit:degreeCelsius"]
        == "degreeCelsius"
    )
    assert (
        QUANTITATIVE_INSTANCE_ALIASES["dtmi:dtdl:extension:quantitativeTypes:v1:unitprefix:kibi"]
        == "kibi"
    )
    assert "dtmi:dtdl:extension:quantitativeTypes:v1:Temperature" not in EXTENSION_ALIASES
    assert "dtmi:dtdl:extension:quantitativeTypes:class:Temperature;1" not in EXTENSION_ALIASES
    assert "dtmi:dtdl:extension:mqtt:class:Mqtt;3" not in EXTENSION_ALIASES
    assert "dtmi:dtdl:extension:mqtt:property:index;3" not in EXTENSION_PROPERTY_ALIASES
    assert EXTENSION_ALIASES["dtmi:dtdl:extension:mqtt:v3:Result"] == "Result"
    assert EXTENSION_PROPERTY_ALIASES["dtmi:dtdl:extension:quantitativeTypes:v1:property:unit"] == (
        "unit",
        "quantitativeTypes",
        1,
    )
    assert "DTDL.FeatureExtension.mqtt.v3.RDF-SHACL.json" in MQTT_V3_METAMODEL_SOURCE
    assert "DTDL.FeatureExtension.mqtt.v1.RDF-SHACL.json" in MQTT_V1_METAMODEL_SOURCE


def test_extension_aliases_match_pinned_context_ids_and_active_versions():
    exact_context_aliases = {
        "dtmi:dtdl:extension:quantitativeTypes:v1:class:Temperature": (
            "Temperature",
            "quantitativeTypes",
            1,
        ),
        "dtmi:dtdl:extension:quantitativeTypes:v1:enum:TemperatureUnit": (
            "TemperatureUnit",
            "quantitativeTypes",
            1,
        ),
        "dtmi:dtdl:extension:annotation:v2:ValueAnnotation": (
            "ValueAnnotation",
            "annotation",
            2,
        ),
        "dtmi:dtdl:extension:overriding:v2:Override": ("Override", "overriding", 2),
        "dtmi:dtdl:extension:historization:v2:Historized": (
            "Historized",
            "historization",
            2,
        ),
        "dtmi:dtdl:extension:requirement:v1:Required": ("Required", "requirement", 1),
        "dtmi:dtdl:extension:mqtt:v1:Mqtt": ("Mqtt", "mqtt", 1),
        "dtmi:dtdl:extension:mqtt:v2:Transparent": ("Transparent", "mqtt", 2),
        "dtmi:dtdl:extension:mqtt:v3:Result": ("Result", "mqtt", 3),
    }
    for alias, metadata in exact_context_aliases.items():
        assert EXTENSION_TYPE_ALIASES[alias] == metadata
        assert extension_alias_metadata(alias) == metadata
        context = {
            "quantitativeTypes": QUANTITATIVE,
            "annotation": ANNOTATION_V2,
            "overriding": OVERRIDING_V2,
            "historization": HISTORIZATION_V2,
            "requirement": REQUIREMENT,
            "mqtt": {
                1: MQTT_V1,
                2: MQTT_V2,
                3: MQTT_V3,
            }.get(metadata[2], MQTT_V1),
        }[metadata[1]]
        assert extension_alias_is_active(alias, (context,))

    assert extension_alias_is_active(
        "dtmi:dtdl:extension:quantitativeTypes:v1:unit:kelvin", (QUANTITATIVE,)
    )
    assert extension_alias_is_active(
        "dtmi:dtdl:extension:quantitativeTypes:v1:property:unit", (QUANTITATIVE,)
    )
    assert extension_alias_is_active("dtmi:dtdl:extension:mqtt:v1:Indexed:index", (MQTT_V1,))
    assert extension_alias_metadata(
        "dtmi:dtdl:extension:annotation:v2:ValueAnnotation:annotates"
    ) == ("annotates", "annotation", 2)
    assert extension_alias_is_active(
        "dtmi:dtdl:extension:annotation:v2:ValueAnnotation:annotates", (ANNOTATION_V2,)
    )
    assert (
        extension_alias_is_active(
            "dtmi:dtdl:extension:annotation:v2:ValueAnnotation:annotates", (ANNOTATION,)
        )
        is False
    )
    assert (
        extension_alias_is_active("dtmi:dtdl:extension:mqtt:v1:Indexed:index", (MQTT_V2,)) is False
    )
    assert (
        extension_alias_is_active("dtmi:dtdl:extension:quantitativeTypes:v1:unit:kelvin", ())
        is False
    )
    assert extension_alias_is_active("dtmi:dtdl:extension:mqtt:class:Mqtt;3", (MQTT_V3,)) is None
    assert "dtmi:dtdl:extension:quantitativeTypes:v1:unit:kelvin" in EXTENSION_ALIAS_METADATA


@pytest.mark.parametrize(
    ("canonical_type", "active_context", "expected_code"),
    [
        (
            "dtmi:dtdl:extension:quantitativeTypes:v1:class:Temperature",
            QUANTITATIVE,
            None,
        ),
        (
            "dtmi:dtdl:extension:quantitativeTypes:v1:Temperature",
            QUANTITATIVE,
            None,
        ),
        (
            "dtmi:dtdl:extension:mqtt:v1:Mqtt",
            MQTT_V2,
            "EXTENSION_VERSION",
        ),
        (
            "dtmi:dtdl:extension:annotation:v2:ValueAnnotation",
            ANNOTATION,
            "EXTENSION_VERSION",
        ),
        (
            "dtmi:dtdl:extension:requirement:v1:Required",
            MQTT_V1,
            "EXTENSION_CONTEXT",
        ),
    ],
)
def test_exact_type_aliases_are_context_version_checked(
    canonical_type, active_context, expected_code
):
    findings = run(
        {**types("Property", canonical_type), "name": "reading", "schema": "double"},
        [active_context],
    )
    codes = {finding.code for finding in findings}
    if expected_code is None:
        assert "EXTENSION_CONTEXT" not in codes
        assert "EXTENSION_VERSION" not in codes
    else:
        assert expected_code in codes


def test_synthetic_source_models_are_conformant_extension_declarations():
    models = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(models) >= 7
    for model in models:
        for element, contexts, pointer, siblings in _walk_model(model):
            findings = validate(
                element, contexts, Source("valid.json", pointer), model["@id"], siblings
            )
            assert not findings, (model["@id"], pointer, findings)


@pytest.mark.parametrize(
    "topic",
    [
        "$SYS/status",
        "vehicles//telemetry",
        "vehicles/{}/telemetry",
        "vehicles/{device-id}/telemetry",
        "vehicles/+/telemetry",
        "vehicles/#",
        "vehicles/a b",
        "vehicles/{id}/{unfinished",
    ],
)
def test_mqtt_rejects_malformed_topic_patterns(topic):
    result = run(
        {**types("Interface", "Mqtt"), "payloadFormat": "Json", "telemetryTopic": topic},
        [MQTT_V1],
    )
    assert any(
        f.code == "EXTENSION_VALUE" and f.source.pointer.endswith("/telemetryTopic") for f in result
    )


@pytest.mark.parametrize("topic", ["devices/{deviceId}/telemetry", "x/y", "a/{device:id}"])
def test_mqtt_accepts_literal_and_token_topic_labels(topic):
    assert not run(
        {**types("Interface", "Mqtt"), "payloadFormat": "Json", "telemetryTopic": topic},
        [MQTT_V1],
    )


@pytest.mark.parametrize("member", ["cmdServiceGroupId", "telemServiceGroupId"])
def test_service_group_ids_are_versioned_and_character_restricted(member):
    valid = {**types("Interface", "Mqtt"), "payloadFormat": "Json", member: "group-1"}
    assert not run(valid, [MQTT_V2])
    for value in ("", "has space", "bad/+id", "é"):
        findings = run({**valid, member: value}, [MQTT_V2])
        assert any(f.code == "EXTENSION_VALUE" for f in findings)
    findings = run(valid, [MQTT_V1])
    assert any(f.code == "EXTENSION_VERSION" for f in findings)


def test_mqtt_payload_format_is_required_and_only_on_interface():
    missing = run(types("Interface", "Mqtt"), [MQTT_V1])
    assert any(f.code == "EXTENSION_REQUIRED" for f in missing)
    wrong_position = run(
        {**types("Telemetry", "Mqtt"), "payloadFormat": "Json"},
        [MQTT_V1],
    )
    assert any(f.code == "EXTENSION_TYPE" for f in wrong_position)


@pytest.mark.parametrize(
    "ttl",
    ["", "15s", "P", "PT", "P1DT", "PT-1S", "PT1Sx", "P1Y2W"],
)
def test_cacheable_ttl_must_be_iso_duration(ttl):
    findings = run(
        {**types("Command", "Cacheable"), "name": "read", "ttl": ttl},
        [MQTT_V1],
    )
    assert any(f.code == "EXTENSION_VALUE" for f in findings)


@pytest.mark.parametrize("ttl", ["PT15S", "P1D", "P1Y2M3DT4H5M6.5S", "PT0S", "P1,5D"])
def test_cacheable_accepts_iso_duration_shapes(ttl):
    assert not run(
        {**types("Command", "Cacheable", "Idempotent"), "name": "read", "ttl": ttl},
        [MQTT_V1],
    )


def test_cacheable_requires_idempotent_per_pinned_mqtt_metamodel():
    findings = run(
        {**types("Command", "Cacheable"), "name": "read", "ttl": "PT1S"},
        [MQTT_V1],
    )
    assert any(f.code == "EXTENSION_CONFLICT" for f in findings)


def test_mqtt_v2_and_v3_adjuncts_are_version_gated():
    transparent = {
        **types("CommandRequest", "Transparent"),
        "schema": {"@type": "Object", "fields": []},
    }
    assert any(f.code == "EXTENSION_VERSION" for f in run(transparent, [MQTT_V1]))
    result = {**types("Object", "Result"), "fields": []}
    assert any(f.code == "EXTENSION_VERSION" for f in run(result, [MQTT_V2]))
    assert not run(transparent, [MQTT_V2])


@pytest.mark.parametrize(
    "raw",
    [
        types("Command", "Indexed"),
        {**types("Property", "Required"), "schema": "string"},
        types("Interface", "Idempotent"),
    ],
)
def test_adjuncts_require_legal_explicit_material_types(raw):
    contexts = [MQTT_V3, HISTORIZATION_V2, REQUIREMENT]
    findings = run(raw, contexts)
    assert any(f.code == "EXTENSION_TYPE" for f in findings)


def test_index_requires_positive_non_boolean_integer_and_unique_siblings():
    for value in (0, -1, True, 1.0, "1", None):
        findings = run(
            {**types("Telemetry", "Indexed"), "name": "x", "index": value},
            [MQTT_V1],
        )
        assert any(f.code == "EXTENSION_VALUE" for f in findings)

    object_schema = {
        **types("Object"),
        "fields": [
            {**types("Field", "Indexed"), "name": "a", "schema": "string", "index": 2},
            {**types("Field", "Indexed"), "name": "b", "schema": "string", "index": 2},
        ],
    }
    findings = run(object_schema, [MQTT_V1])
    assert any(f.code == "EXTENSION_DUPLICATE" for f in findings)
    assert any(f.source.pointer.endswith("/fields/1/index") for f in findings)


def test_telemetry_index_uniqueness_uses_effective_sibling_declarations():
    first = {**types("Telemetry", "Indexed"), "name": "a", "schema": "integer", "index": 3}
    second = {**types("Telemetry", "Indexed"), "name": "b", "schema": "integer", "index": 3}
    siblings = {"a": first, "b": second}
    findings = run(second, [MQTT_V1], siblings)
    assert any(f.code == "EXTENSION_DUPLICATE" for f in findings)


def test_transparent_rejects_inline_non_object_but_allows_named_schema_reference():
    assert any(
        f.code == "EXTENSION_SCHEMA"
        for f in run(
            {**types("CommandRequest", "Transparent"), "schema": "string"},
            [MQTT_V2],
        )
    )
    assert not run(
        {
            **types("CommandRequest", "Transparent"),
            "schema": "dtmi:example:RequestObject;1",
        },
        [MQTT_V2],
    )


def test_result_error_shape_constraints_and_required_conflict():
    bad_result = {
        **types("Object", "Result"),
        "fields": [
            {**types("Field", "NormalResult", "Required"), "name": "ok", "schema": "string"},
            {**types("Field", "NormalResult"), "name": "ok2", "schema": "string"},
            {**types("Field", "ErrorResult"), "name": "err", "schema": "string"},
            {"@type": "Field", "name": "unmarked", "schema": "string"},
        ],
    }
    findings = run(bad_result, [MQTT_V3, REQUIREMENT])
    assert {f.code for f in findings} >= {
        "EXTENSION_CARDINALITY",
        "EXTENSION_CONFLICT",
        "EXTENSION_SCHEMA",
        "EXTENSION_SHAPE",
    }

    valid_error = {
        **types("Object", "Error"),
        "fields": [{**types("Field", "ErrorMessage"), "name": "message", "schema": "string"}],
    }
    assert not run(valid_error, [MQTT_V3])
    invalid_message = {
        **types("Object", "Error"),
        "fields": [{**types("Field", "ErrorMessage"), "name": "message", "schema": "integer"}],
    }
    assert any(f.code == "EXTENSION_SCHEMA" for f in run(invalid_message, [MQTT_V3]))
    misplaced_result_field = {
        **types("Object"),
        "fields": [{**types("Field", "NormalResult"), "name": "value", "schema": "integer"}],
    }
    assert any(f.code == "EXTENSION_POSITION" for f in run(misplaced_result_field, [MQTT_V3]))


def test_annotation_v2_references_effective_siblings_and_requires_context():
    annotation = {
        **types("Property", "ValueAnnotation"),
        "name": "details",
        "annotates": "baseReading",
        "schema": "string",
    }
    effective_inherited = {
        "baseReading": {**types("Telemetry"), "name": "baseReading", "schema": "double"}
    }
    assert not run(annotation, [ANNOTATION_V2], effective_inherited)
    missing = run(annotation, [MQTT_V1], effective_inherited)
    assert any(f.code == "EXTENSION_CONTEXT" for f in missing)
    assert any(
        f.code == "EXTENSION_REFERENCE"
        for f in run({**annotation, "annotates": "absent"}, [ANNOTATION_V2], {})
    )
    wrong_kind = {"baseReading": {**types("Command"), "name": "baseReading"}}
    assert any(
        f.code == "EXTENSION_REFERENCE" for f in run(annotation, [ANNOTATION_V2], wrong_kind)
    )
    assert not run(annotation, [ANNOTATION], effective_inherited)


def test_override_requires_annotation_property_known_target_and_matching_schema():
    target = {
        **types("Telemetry", "Temperature"),
        "name": "reading",
        "schema": "double",
        "unit": "degreeFahrenheit",
    }
    override = {
        **types("Property", "ValueAnnotation", "Override"),
        "name": "readingUnit",
        "annotates": "reading",
        "overrides": "unit",
        "schema": "TemperatureUnit",
    }
    contexts = [QUANTITATIVE, ANNOTATION_V2, OVERRIDING_V2]
    assert not run(override, contexts, {"reading": target})
    assert not run(
        {**override, "schema": "dtmi:dtdl:extension:quantitativeTypes:v1:enum:TemperatureUnit"},
        contexts,
        {"reading": target},
    )
    assert any(
        f.code == "EXTENSION_SCHEMA"
        for f in run({**override, "schema": "string"}, contexts, {"reading": target})
    )
    assert any(
        f.code == "EXTENSION_REFERENCE"
        for f in run(
            {**override, "overrides": "dtmi:evil:extension:unit;1"},
            contexts,
            {"reading": target},
        )
    )
    assert any(
        f.code == "EXTENSION_SCHEMA"
        for f in run(
            {**override, "schema": "dtmi:evil:TemperatureUnit;9"},
            contexts,
            {"reading": target},
        )
    )
    assert any(
        f.code == "EXTENSION_SCHEMA"
        for f in run(
            {
                **override,
                "schema": ("dtmi:dtdl:extension:quantitativeTypes:class:TemperatureUnit;2"),
            },
            contexts,
            {"reading": target},
        )
    )
    assert any(
        f.code == "EXTENSION_REFERENCE"
        for f in run(
            {
                **override,
                "overrides": "dtmi:dtdl:extension:quantitativeTypes:property:unit;2",
            },
            contexts,
            {"reading": target},
        )
    )
    assert any(
        f.code == "EXTENSION_CONTEXT"
        for f in run(override, [QUANTITATIVE, OVERRIDING_V2], {"reading": target})
    )
    assert not run(
        override,
        [QUANTITATIVE, ANNOTATION, OVERRIDING],
        {"reading": target},
    )
    illegal_material = {
        **types("Telemetry", "ValueAnnotation", "Override"),
        "name": "readingUnit",
        "annotates": "reading",
        "overrides": "unit",
        "schema": "TemperatureUnit",
    }
    assert any(
        f.code == "EXTENSION_TYPE"
        for f in run(
            illegal_material,
            [QUANTITATIVE, ANNOTATION_V2, OVERRIDING_V2],
            {"reading": target},
        )
    )

    indexed_target = {
        **types("Telemetry", "Indexed"),
        "name": "indexedReading",
        "schema": "integer",
        "index": 4,
    }
    indexed_override = {
        **types("Property", "ValueAnnotation", "Override"),
        "name": "readingIndex",
        "annotates": "indexedReading",
        "overrides": "index",
        "schema": "integer",
    }
    assert not run(
        indexed_override,
        [MQTT_V1, ANNOTATION_V2, OVERRIDING_V2],
        {"indexedReading": indexed_target},
    )
    version_mismatch = run(
        {
            **indexed_override,
            "overrides": "dtmi:dtdl:extension:mqtt:v1:Indexed:index",
        },
        [MQTT_V2, ANNOTATION_V2, OVERRIDING_V2],
        {"indexedReading": indexed_target},
    )
    assert any(f.code == "EXTENSION_VERSION" for f in version_mismatch)


@pytest.mark.parametrize("context", [HISTORIZATION, HISTORIZATION_V2])
def test_historized_property_and_telemetry_have_distinct_source_semantics(context):
    for material in ("Property", "Telemetry"):
        raw = {**types(material, "Historized"), "name": "value", "schema": "double"}
        assert not run(raw, [context])
        assert semantics(raw, (context,))["historization"]["historized"] is True


def test_requirement_models_optional_default_and_explicit_required_presence():
    required = {**types("Field", "Required"), "name": "x", "schema": "double"}
    optional = {**types("Field"), "name": "y", "schema": "double"}
    assert not run(required, [REQUIREMENT])
    assert semantics(required, (REQUIREMENT,))["presence"]["required"] is True
    assert semantics(optional, (REQUIREMENT,))["presence"]["required"] is False
    assert semantics(optional, (REQUIREMENT,))["presence"]["default"] == "optional"
    assert any(f.code == "EXTENSION_CONTEXT" for f in run(required, [MQTT_V1]))


def test_geospatial_registry_covers_term_and_canonical_aliases_without_lossy_target_claims():
    assert set(GEOSCHEMAS) == {
        "point",
        "lineString",
        "polygon",
        "multiPoint",
        "multiLineString",
        "multiPolygon",
    }
    assert len(GEO_ALIASES) == 6
    for name, schema in GEOSCHEMAS.items():
        assert schema["@id"] == f"dtmi:standard:schema:geospatial:{name};3"
        assert GEO_ALIASES[schema["@id"]] == name
        for source_schema in (name, schema["@id"]):
            interpreted = semantics({"schema": source_schema}, ())
            assert interpreted["geospatial"]["@id"] == schema["@id"]
            assert interpreted["geospatial"]["geoJsonType"]
            assert "coordinates" not in interpreted["geospatial"]


@pytest.mark.parametrize(
    ("name", "geometry", "coordinate_ids"),
    [
        ("point", "Point", ["position"]),
        ("lineString", "LineString", ["lineStringCoordinateArray", "position"]),
        (
            "polygon",
            "Polygon",
            ["polygonCoordinateArray", "linearRingCoordinateArray", "position"],
        ),
        ("multiPoint", "MultiPoint", ["positionArray", "position"]),
        (
            "multiLineString",
            "MultiLineString",
            ["lineStringCoordinateArrayArray", "lineStringCoordinateArray", "position"],
        ),
        (
            "multiPolygon",
            "MultiPolygon",
            [
                "polygonCoordinateArrayArray",
                "polygonCoordinateArray",
                "linearRingCoordinateArray",
                "position",
            ],
        ),
    ],
)
def test_geospatial_source_schemas_have_parser_verified_object_enum_and_coordinate_shapes(
    name, geometry, coordinate_ids
):
    schema = GEOSCHEMAS[name]
    source_schema = schema["source_schema"]
    assert set(schema) == {"@id", "term", "geoJsonType", "source_schema"}
    assert source_schema["@id"] == schema["@id"]
    assert source_schema["@type"] == "Object"
    assert [field["name"] for field in source_schema["fields"]] == ["type", "coordinates"]

    type_schema = source_schema["fields"][0]["schema"]
    assert type_schema == {
        "@id": f"dtmi:standard:schema:geospatial{geometry}Type;3",
        "@type": "Enum",
        "valueSchema": "string",
        "enumValues": [{"name": name, "enumValue": geometry}],
    }

    coordinates = source_schema["fields"][1]["schema"]
    observed_ids = []
    while isinstance(coordinates, dict):
        assert coordinates["@type"] == "Array"
        observed_ids.append(coordinates["@id"])
        coordinates = coordinates["elementSchema"]
    assert observed_ids == [
        f"dtmi:standard:schema:geospatial:{coordinate_id};3" for coordinate_id in coordinate_ids
    ]
    assert coordinates == "double"


def test_extension_semantics_preserve_mqtt_wire_and_annotation_source_details():
    mqtt = {
        **types("Interface", "Mqtt"),
        "payloadFormat": "Protobuf/3",
        "telemetryTopic": "device/{deviceId}/telemetry",
    }
    result = semantics(mqtt, (MQTT_V1,))
    assert result["mqtt"]["version"] == 1
    assert result["mqtt"]["properties"]["telemetryTopic"] == mqtt["telemetryTopic"]
    annotated = {
        **types("Property", "ValueAnnotation", "Override"),
        "annotates": "temperature",
        "overrides": "unit",
    }
    assert semantics(annotated, (ANNOTATION_V2, OVERRIDING_V2))["annotation"] == {
        "version": 2,
        "annotates": "temperature",
        "override": "unit",
    }
