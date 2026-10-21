from dataclasses import replace

import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.plan import EntityPlan, PropertyPlan, RelationshipPlan, make_plan
from dtdl_to_ontology.preflight import complex_metrics, preflight
from dtdl_to_ontology.resolver import resolve

from .conftest import interface

PRIMITIVE = {"kind": "primitive", "dataType": "string"}


@pytest.fixture
def plan(write_models):
    return make_plan(resolve(load(write_models(interface()))))


def codes(plan):
    return {finding.code for finding in preflight(plan).findings}


@pytest.mark.parametrize("kind,limit", [("entities", 10_000), ("relationships", 10_000)])
def test_actual_item_count_boundary_and_one_over(plan, kind, limit):
    identity, entity = next(iter(plan.entities.items()))
    if kind == "entities":
        plan.entities = {
            f"dtmi:example:E{i};1": EntityPlan(f"dtmi:example:E{i};1", entity.source)
            for i in range(limit)
        }
        assert "LIMIT_ENTITIES" not in codes(plan)
        plan.entities[identity] = entity
        assert "LIMIT_ENTITIES" in codes(plan)
    else:
        plan.relationships = [
            RelationshipPlan(f"{identity}/r{i}", identity, identity, entity.source)
            for i in range(limit)
        ]
        assert "LIMIT_RELATIONSHIPS" not in codes(plan)
        plan.relationships.append(
            RelationshipPlan(
                identity + "/extra",
                identity,
                identity,
                entity.source,
            )
        )
        assert "LIMIT_RELATIONSHIPS" in codes(plan)


def test_properties_annotations_and_text_boundaries(plan):
    identity, entity = next(iter(plan.entities.items()))
    entity.properties = [
        PropertyPlan(f"p{i}", entity.source, identity, PRIMITIVE) for i in range(1000)
    ]
    entity.annotations = {f"a{i}": "value" for i in range(100)}
    entity.description = "x" * 4000
    assert not codes(plan)
    entity.properties.append(PropertyPlan("extra", entity.source, identity, PRIMITIVE))
    entity.annotations["extra"] = "x" * 4001
    entity.description += "x"
    assert {"LIMIT_PROPERTIES", "LIMIT_ANNOTATIONS", "LIMIT_TEXT"} <= codes(plan)


def test_ordinary_name_boundary_and_whole_document_bounds(plan):
    entity = next(iter(plan.entities.values()))
    entity.annotations = {"x" * 512: "value"}
    assert "LIMIT_NAME" not in codes(plan)
    entity.annotations = {"x" * 513: "value"}
    assert "LIMIT_NAME" in codes(plan)
    entity.annotations = {}
    measured = preflight(plan).measurements
    plan.profile = replace(
        plan.profile,
        max_document_nodes=measured["document_nodes"],
        max_document_depth=measured["document_depth"],
    )
    assert not codes(plan)
    plan.profile = replace(
        plan.profile,
        max_document_nodes=measured["document_nodes"] - 1,
        max_document_depth=measured["document_depth"] - 1,
    )
    assert {"LIMIT_DOCUMENT_NODES", "LIMIT_DOCUMENT_DEPTH"} <= codes(plan)


def struct(children):
    return {
        "kind": "struct",
        "fields": [{"name": f"f{i}", "type": shape} for i, shape in enumerate(children)],
    }


def tree(nodes):
    if nodes == 1:
        return PRIMITIVE
    children = []
    remaining = nodes - 1
    while remaining:
        size = min(remaining, 1025)
        children.append(PRIMITIVE if size == 1 else struct([PRIMITIVE] * (size - 1)))
        remaining -= size
    return struct(children)


def test_complex_node_depth_and_field_actual_boundaries(plan):
    identity, entity = next(iter(plan.entities.items()))
    prop = PropertyPlan("shape", entity.source, identity, tree(4096))
    entity.properties = [prop]
    assert complex_metrics(prop.logical_type)[0] == 4096
    assert "LIMIT_COMPLEX_NODES" not in codes(plan)
    prop.logical_type = tree(4097)
    assert "LIMIT_COMPLEX_NODES" in codes(plan)
    shape = PRIMITIVE
    for _ in range(31):
        shape = struct([shape])
    prop.logical_type = shape
    assert "LIMIT_COMPLEX_DEPTH" not in codes(plan)
    prop.logical_type = struct([shape])
    assert "LIMIT_COMPLEX_DEPTH" in codes(plan)
    prop.logical_type = struct([PRIMITIVE] * 1024)
    assert "LIMIT_STRUCT_FIELDS" not in codes(plan)
    prop.logical_type = struct([PRIMITIVE] * 1025)
    assert "LIMIT_STRUCT_FIELDS" in codes(plan)
