import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.vocabulary import ANNOTATION, OVERRIDING, QUANTITATIVE

from .conftest import interface


def property_(name="value", schema="double"):
    return {"@type": "Property", "name": name, "schema": schema}


def test_shared_schema_dag_is_validated_without_exponential_expansion(write_models):
    schemas = []
    for index in range(25):
        target = "string" if index == 0 else f"dtmi:example:S{index - 1};1"
        schemas.append(
            {
                "@id": f"dtmi:example:S{index};1",
                "@type": "Object",
                "fields": [{"name": "left", "schema": target}, {"name": "right", "schema": target}],
            }
        )
    result = resolve(load(write_models(interface(schemas=schemas))))
    assert {f.code for f in result.findings} == {"DTDL_SCHEMA_DEPTH"}
    assert len(result.schemas) == 25


def test_malformed_enum_value_schema_reports_instead_of_crashing(write_models):
    schema = {"@type": "Enum", "valueSchema": {}, "enumValues": []}
    result = resolve(load(write_models(interface(contents=[property_(schema=schema)]))))
    assert any(f.code == "SCHEMA_SHAPE" for f in result.findings)


@pytest.mark.parametrize(
    "primitive,entries",
    [
        ("string", [None]),
        ("string", [{"name": "On"}]),
        ("string", [{"name": "On", "enumValue": 1}]),
        ("integer", [{"name": "On", "enumValue": True}]),
        ("integer", [{"name": "On", "enumValue": 2**31}]),
        ("string", [{"name": "On", "enumValue": {}}]),
        ("string", [{"name": "On", "enumValue": "a"}, {"name": "On", "enumValue": "b"}]),
        ("string", [{"name": "On", "enumValue": "a"}, {"name": "Off", "enumValue": "a"}]),
        ("string", [{"name": "1On", "enumValue": "a"}]),
        ("string", [{"name": "On", "enumValue": "a", "@type": "Property"}]),
    ],
)
def test_enum_source_literals_and_names_are_validated(write_models, primitive, entries):
    schema = {"@type": "Enum", "valueSchema": primitive, "enumValues": entries}
    result = resolve(load(write_models(interface(contents=[property_(schema=schema)]))))
    findings = [f for f in result.findings if f.code == "ENUM_VALUE"]
    assert findings
    assert all("/contents/0/schema/enumValues/" in f.source.pointer for f in findings)


@pytest.mark.parametrize("primitive", ["string", "integer"])
@pytest.mark.parametrize("values", [{}, {"enumValues": []}])
def test_enum_choices_are_optional_in_dtdlv3(write_models, primitive, values):
    schema = {"@type": "Enum", "valueSchema": primitive, **values}
    result = resolve(load(write_models(interface(contents=[property_(schema=schema)]))))
    assert not result.findings


@pytest.mark.parametrize(
    "fields",
    [
        {"minMultiplicity": 1},
        {"minMultiplicity": False},
        {"minMultiplicity": "many"},
        {"maxMultiplicity": 0},
        {"maxMultiplicity": True},
        {"maxMultiplicity": 2**31},
        {"writable": "true"},
        {"target": {}},
        {"target": "not-a-dtmi"},
        {"properties": [property_(), property_()]},
        {"properties": [{"@type": "Telemetry", "name": "reading", "schema": "double"}]},
        {"properties": [{"@type": "Property", "schema": "double"}]},
    ],
)
def test_malformed_relationship_source_is_rejected_before_policies(write_models, fields):
    raw = {"@type": "Relationship", "name": "contains", **fields}
    result = resolve(load(write_models(interface(contents=[raw]))))
    assert any(f.code in {"CONTENT_SHAPE", "CONTENT_TYPE"} for f in result.findings)
    assert all("/contents/0/" in f.source.pointer for f in result.findings)


@pytest.mark.parametrize("unit", [{}, False, None])
def test_malformed_quantitative_units_are_diagnostics_not_type_errors(write_models, unit):
    root = interface(
        contents=[
            {
                "@type": ["Property", "Temperature"],
                "name": "reading",
                "schema": "double",
                "unit": unit,
            }
        ],
        **{"@context": ["dtmi:dtdl:context;3", QUANTITATIVE]},
    )
    result = resolve(load(write_models(root)))
    assert any(
        f.code == "QUANTITY_UNIT" and f.source.pointer.endswith("/unit") for f in result.findings
    )


def test_valid_relationship_metadata_and_property_state_still_resolve(write_models):
    root = interface(
        contents=[
            {
                "@type": "Relationship",
                "name": "contains",
                "minMultiplicity": 0,
                "maxMultiplicity": 1,
                "target": "dtmi:example:Target;1",
                "writable": False,
                "properties": [property_("status", "string")],
            }
        ]
    )
    assert not resolve(load(write_models(root))).findings


def test_cross_partition_private_schema_is_rejected_and_preserves_location(write_models):
    schema = {
        "@id": "dtmi:example:Address;1",
        "@type": "Object",
        "fields": [{"name": "street", "schema": "string"}],
    }
    result = resolve(
        load(
            write_models(
                interface("Schemas", schemas=[schema]),
                interface("Building", [property_(schema=schema["@id"])]),
            )
        )
    )
    assert {f.code for f in result.findings} == {"PARTITION_REFERENCE"}
    declaration = result.schemas[schema["@id"]]
    assert declaration.source.pointer == "/0/schemas/0"
    assert "dtmi:example:Building;1" not in result.references


@pytest.mark.parametrize(
    "contents,code",
    [
        ([property_(schema="dtmi:example:Absent;1")], "MISSING_SCHEMA"),
        (
            [{"@type": "Component", "name": "part", "schema": "dtmi:example:Absent;1"}],
            "MISSING_COMPONENT",
        ),
        ([property_(schema={"@type": "Object", "fields": "invalid"})], "SCHEMA_SHAPE"),
    ],
)
def test_missing_or_invalid_schema(write_models, contents, code):
    result = resolve(load(write_models(interface(contents=contents))))
    assert any(
        f.code == code and f.source.pointer.startswith("/0/contents/") for f in result.findings
    )


def test_schema_cycle_does_not_recurse_forever(write_models):
    schema = {
        "@id": "dtmi:example:Recursive;1",
        "@type": "Object",
        "fields": [{"name": "next", "schema": "dtmi:example:Recursive;1"}],
    }
    result = resolve(
        load(
            write_models(
                interface(
                    contents=[property_(schema=schema["@id"])],
                    schemas=[schema],
                )
            )
        )
    )
    assert any(f.code == "SCHEMA_CYCLE" for f in result.findings)


def test_inheritance_cycle_and_missing_parent(write_models):
    a = interface("A", extends="dtmi:example:B;1")
    b = interface("B", extends=["dtmi:example:A;1", "dtmi:example:Absent;1"])
    result = resolve(load(write_models(a, b)))
    assert {f.code for f in result.findings} >= {"INHERITANCE_CYCLE", "MISSING_PARENT"}


def test_diamond_preserves_one_declaring_origin_and_both_parent_paths(write_models):
    root = interface("Root", [property_()])
    left = interface("Left", extends=root["@id"])
    right = interface("Right", extends=root["@id"])
    child = interface("Child", extends=[right["@id"], left["@id"]])
    result = resolve(load(write_models(child, right, root, left)))
    assert not result.findings
    assert list(result.contents[child["@id"]]) == ["value"]
    assert [d.owner for d in result.origins[child["@id"]]["value"]] == [root["@id"]]
    assert result.parents[child["@id"]] == [left["@id"], right["@id"]]


def test_incompatible_inherited_names_do_not_overwrite(write_models):
    left = interface("Left", [property_(schema="double")])
    right = interface("Right", [property_(schema="string")])
    child = interface("Child", extends=[left["@id"], right["@id"]])
    result = resolve(load(write_models(child, left, right)))
    conflict = next(f for f in result.findings if f.code == "CONTENT_CONFLICT")
    assert conflict.dtmi == child["@id"]
    assert "/1/contents/0" in conflict.message
    assert "/2/contents/0" in conflict.message
    assert conflict.blocking


def test_invalid_schema_collection_reports_error(write_models):
    result = resolve(load(write_models(interface(schemas=None))))
    assert any(f.code == "SCHEMA_SHAPE" for f in result.findings)


def test_unit_schema_and_instance_override_are_retained(write_models):
    value = {**property_(), "@type": ["Property", "Temperature"], "unit": "degreeCelsius"}
    unit = {
        **property_("valueUnit", "TemperatureUnit"),
        "@type": ["Property", "ValueAnnotation", "Override"],
        "annotates": "value",
        "overrides": "unit",
    }
    model = interface(contents=[value, unit])
    model["@context"] = ["dtmi:dtdl:context;3", QUANTITATIVE, ANNOTATION, OVERRIDING]
    result = resolve(load(write_models(model)))
    assert not result.findings
    assert result.contents[model["@id"]]["valueUnit"].raw == unit
    assert "redefines" not in result.contents[model["@id"]]["valueUnit"].raw


@pytest.mark.parametrize(
    "change,code",
    [
        ({"@context": ["dtmi:dtdl:context;3", "dtmi:example:extension;1"]}, "UNKNOWN_EXTENSION"),
        (
            {"contents": [{"@type": "Property", "name": "unit", "schema": "TemperatureUnit"}]},
            "EXTENSION_CONTEXT",
        ),
        (
            {
                "contents": [
                    {
                        "@type": ["Property", "Temperature"],
                        "name": "temp",
                        "schema": "string",
                        "unit": "metre",
                    }
                ]
            },
            "QUANTITY_SCHEMA",
        ),
    ],
)
def test_unknown_or_invalid_extension_is_not_silently_ignored(write_models, change, code):
    result = resolve(load(write_models(interface(**change))))
    assert any(f.code == code for f in result.findings)
