import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.resolver import resolve

from .conftest import interface


@pytest.mark.parametrize("literal", [True, 1, "value"])
@pytest.mark.parametrize(
    "datatype", [[], ["xsd:string", "xsd:string"], [None], {}, {"name": "xsd:string"}]
)
def test_invalid_literal_type_is_a_diagnostic_not_a_crash(write_models, literal, datatype):
    model = interface(
        contents=[
            {
                "@type": "Property",
                "name": "value",
                "schema": "boolean",
                "writable": {"@value": literal, "@type": datatype},
            }
        ]
    )
    result = resolve(load(write_models(model)))
    assert "LITERAL" in {f.code for f in result.collection.findings + result.findings}


@pytest.mark.parametrize("prefix", ["xsd:", "http://www.w3.org/2001/XMLSchema#"])
@pytest.mark.parametrize("kind,value", [("boolean", True), ("integer", 3), ("string", "hello")])
def test_literal_type_accepts_a_singleton_array(write_models, prefix, kind, value):
    literal = {"@value": value, "@type": [prefix + kind]}
    if kind == "string":
        model = interface(comment=literal)
    elif kind == "integer":
        model = interface(
            contents=[{"@type": "Relationship", "name": "r", "maxMultiplicity": literal}]
        )
    else:
        model = interface(
            contents=[{"@type": "Property", "name": "p", "schema": "boolean", "writable": literal}]
        )
    result = resolve(load(write_models(model)))
    assert not result.collection.findings + result.findings


def test_relationship_target_is_a_dtmi_not_a_representational_literal(write_models):
    model = interface(
        contents=[
            {
                "@type": "Relationship",
                "name": "contains",
                "target": {"@value": "dtmi:example:Target;1"},
            }
        ]
    )
    result = resolve(load(write_models(model)))
    assert "CONTENT_SHAPE" in {f.code for f in result.findings}


@pytest.mark.parametrize("kind", ["Array", "Map", "Object"])
@pytest.mark.parametrize("depth,blocked", [(5, False), (6, True)])
def test_primitive_terminal_counts_toward_schema_depth(write_models, kind, depth, blocked):
    schema = "string"
    for _ in range(depth):
        if kind == "Array":
            schema = {"@type": kind, "elementSchema": schema}
        elif kind == "Map":
            schema = {
                "@type": kind,
                "mapKey": {"name": "key", "schema": "string"},
                "mapValue": {"name": "value", "schema": schema},
            }
        else:
            schema = {"@type": kind, "fields": [{"name": "value", "schema": schema}]}
    result = resolve(
        load(
            write_models(interface(contents=[{"@type": "Property", "name": "v", "schema": schema}]))
        )
    )
    assert any(f.code == "DTDL_SCHEMA_DEPTH" for f in result.findings) == blocked
