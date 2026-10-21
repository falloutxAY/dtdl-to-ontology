import json
from dataclasses import replace

import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.profile import DEFAULT_PROFILE
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.tmdl import render_entity, render_relationships

from .conftest import interface


def test_fixed_object_syntax_is_renderable_but_unbound_publication_is_blocked(write_models):
    root = interface(
        contents=[
            {
                "@type": "Property",
                "name": "location",
                "description": "A location\nentity 'not a declaration'",
                "schema": {
                    "@type": "Object",
                    "fields": [
                        {"name": "latitude", "schema": "double"},
                        {"name": "label", "schema": "string"},
                    ],
                },
            }
        ]
    )
    plan = make_plan(resolve(load(write_models(root))))
    assert plan.blocked
    assert any(f.code == "UNBOUND_STRUCT" and f.blocking for f in plan.findings)
    text = render_entity(plan.entities[root["@id"]])
    assert "\t\tdataType: complex\n" in text
    assignment = next(line for line in text.splitlines() if "complexDataType" in line)
    assert assignment == (
        '\t\tcomplexDataType = {"fields": [{"name": "latitude", '
        '"type": {"dataType": "double", "kind": "primitive"}}, {"name": "label", '
        '"type": {"dataType": "string", "kind": "primitive"}}], "kind": "struct"}'
    )
    assert "\t/// entity 'not a declaration'" in text
    assert "backing" not in text and "keyProperty" not in text


def test_collection_enum_and_temporal_fallbacks_require_their_own_policies(write_models):
    root = interface(
        contents=[
            {
                "@type": "Property",
                "name": "items",
                "schema": {"@type": "Array", "elementSchema": "string"},
            },
            {"@type": "Property", "name": "day", "schema": "date"},
            {
                "@type": "Property",
                "name": "choice",
                "schema": {
                    "@type": "Enum",
                    "valueSchema": "string",
                    "enumValues": [{"name": "On", "enumValue": "on"}],
                },
            },
        ]
    )
    resolution = resolve(load(write_models(root)))
    assert make_plan(resolution, Options(compatibility=True)).blocked
    plan = make_plan(
        resolution,
        Options(
            compatibility=True,
            policies=frozenset({"json-collections", "enum-underlying", "temporal-strings"}),
        ),
    )
    assert not plan.blocked
    text = render_entity(plan.entities[root["@id"]])
    assert text.count("dataType: string") == 3
    assert "complexDataType" not in text
    assert {p.original["name"] for p in plan.entities[root["@id"]].properties} == {
        "items",
        "day",
        "choice",
    }
    assert not any(
        json.dumps(p.logical_type).find('"kind": "array"') >= 0
        for p in plan.entities[root["@id"]].properties
    )


def test_inherited_edges_are_explicit_and_unverified_output_is_blocked(write_models):
    target = interface("Target")
    base = interface(
        "Base",
        [
            {"@type": "Relationship", "name": "contains", "target": target["@id"]},
        ],
    )
    child = interface("Child", extends=base["@id"])
    resolution = resolve(load(write_models(base, child, target)))
    options = Options(compatibility=True, policies=frozenset({"flatten-inheritance"}))
    blocked = make_plan(resolution, options)
    with pytest.raises(ValueError, match="blocking"):
        render_relationships(blocked)
    profile = replace(
        DEFAULT_PROFILE,
        unbound_relationships=True,
        relationship_evidence="Synthetic test-only contract.",
    )
    plan = make_plan(resolution, options, profile)
    assert {r.from_entity for r in plan.relationships} == {base["@id"], child["@id"]}
    text = render_relationships(plan)
    assert text.count("entityRelationship ") == 2
    assert text.count("fromEntity: ") == 2
    assert "backing" not in text and "table" not in text
