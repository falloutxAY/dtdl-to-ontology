from dataclasses import replace

import pytest

from dtdl_to_ontology.definition import build_parts
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.manifest import build_manifest
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.tmdl import render_entity

from .conftest import interface


def test_native_single_parent_is_opt_in_and_never_picks_multiple_parent(write_models):
    base = interface("Base", [{"@type": "Property", "name": "label", "schema": "string"}])
    child = interface("Child", extends=base["@id"])
    resolution = resolve(load(write_models(base, child)))
    assert make_plan(resolution).blocked
    flat = make_plan(
        resolution,
        Options(
            compatibility=True,
            policies=frozenset({"flatten-inheritance"}),
        ),
    )
    assert not flat.blocked
    assert len(flat.entities[child["@id"]].properties) == 1
    assert "baseEntityType" not in render_entity(flat.entities[child["@id"]])
    native = make_plan(resolution, Options(inheritance=True))
    assert not native.blocked
    assert not native.entities[child["@id"]].properties
    assert "baseEntityType:" in render_entity(native.entities[child["@id"]])
    other = interface("Other")
    multiple = interface("Multiple", extends=[base["@id"], other["@id"]])
    plan = make_plan(resolve(load(write_models(base, other, multiple))), Options(inheritance=True))
    assert plan.blocked
    assert plan.entities[multiple["@id"]].base is None


def test_components_are_structs_with_identity_loss_and_no_silent_contained_edges(write_models):
    detail = interface(
        "Detail",
        [
            {"@type": "Property", "name": "label", "schema": "string"},
            {"@type": "Relationship", "name": "related", "target": "dtmi:example:Detail;1"},
        ],
    )
    root = interface("Root", [{"@type": "Component", "name": "detail", "schema": detail["@id"]}])
    resolution = resolve(load(write_models(root, detail)))
    options = Options(
        compatibility=True,
        policies=frozenset({"component-properties", "omit-relationships"}),
        omissions=frozenset({root["@id"] + "/detail/related", detail["@id"] + "/related"}),
    )
    plan = make_plan(resolution, options)
    assert any(f.code == "UNBOUND_STRUCT" and f.blocking for f in plan.findings)
    plan = make_plan(resolution, replace(options, policies=options.policies | {"json-objects"}))
    assert not plan.blocked
    prop = plan.entities[root["@id"]].properties[0]
    assert prop.logical_type == {"kind": "primitive", "dataType": "string"}
    shape = prop.pre_fallback_logical_type
    assert shape == {
        "kind": "struct",
        "fields": [
            {"name": "label", "type": {"kind": "primitive", "dataType": "string"}},
        ],
    }
    blocked = make_plan(
        resolution,
        Options(
            compatibility=True,
            policies=frozenset({"component-properties", "json-objects"}),
        ),
    )
    assert any(f.code == "COMPONENT_RELATIONSHIP" and f.blocking for f in blocked.findings)


def test_recursive_components_block_without_recursing_forever(write_models):
    root = interface(
        contents=[
            {"@type": "Component", "name": "self", "schema": "dtmi:example:Example;1"},
        ]
    )
    plan = make_plan(
        resolve(load(write_models(root))),
        Options(
            compatibility=True,
            policies=frozenset({"component-properties"}),
        ),
    )
    assert any(f.code == "COMPONENT_CYCLE" and f.blocking for f in plan.findings)


@pytest.mark.parametrize("named", [False, True])
def test_fixed_objects_require_separate_approval_and_preserve_full_shape(write_models, named):
    schema = {
        "@type": "Object",
        "fields": [
            {
                "name": "point",
                "schema": {
                    "@type": "Object",
                    "fields": [{"name": "x", "schema": "double"}],
                },
            },
        ],
    }
    root = interface(contents=[{"@type": "Property", "name": "position", "schema": schema}])
    if named:
        schema["@id"] = "dtmi:example:Position;1"
        root["schemas"] = [schema]
        root["contents"][0]["schema"] = schema["@id"]
    resolution = resolve(load(write_models(root)))
    for policies in (frozenset(), frozenset({"json-collections", "component-properties"})):
        blocked = make_plan(resolution, Options(compatibility=True, policies=policies))
        assert any(f.code == "UNBOUND_STRUCT" and f.blocking for f in blocked.findings)
        with pytest.raises(ValueError, match="blocking"):
            build_parts(blocked, "Blocked")
    plan = make_plan(resolution, Options(compatibility=True, policies=frozenset({"json-objects"})))
    assert not plan.blocked
    prop = plan.entities[root["@id"]].properties[0]
    assert prop.logical_type == {"kind": "primitive", "dataType": "string"}
    assert prop.pre_fallback_logical_type == {
        "kind": "struct",
        "fields": [
            {
                "name": "point",
                "type": {
                    "kind": "struct",
                    "fields": [{"name": "x", "type": {"kind": "primitive", "dataType": "double"}}],
                },
            }
        ],
    }
    manifest = build_manifest(plan)
    mapped = manifest["target_entities"][root["@id"]]["properties"][0]
    assert mapped["original"] == root["contents"][0]
    assert mapped["pre_fallback_logical_type"] == prop.pre_fallback_logical_type
    assert manifest["source_models"][root["@id"]]["definition"] == root
    (finding,) = [f for f in plan.findings if f.code == "UNBOUND_STRUCT"]
    assert finding.approved and finding.source.pointer == "/0/contents/0"
    parts = "\n".join(build_parts(plan, "Approved").values())
    assert "complexDataType" not in parts and "backingConfiguration" not in parts


def test_nested_component_cannot_be_approved_by_json_policies(write_models):
    leaf = interface("Leaf", [{"@type": "Property", "name": "label", "schema": "string"}])
    detail = interface("Detail", [{"@type": "Component", "name": "inner", "schema": leaf["@id"]}])
    root = interface("Root", [{"@type": "Component", "name": "detail", "schema": detail["@id"]}])
    resolution = resolve(load(write_models(root, detail, leaf)))
    options = Options(compatibility=True, policies=frozenset({"json-objects"}))
    assert any(
        f.code == "COMPONENT" and f.blocking for f in make_plan(resolution, options).findings
    )
    plan = make_plan(
        resolution, replace(options, policies=options.policies | {"component-properties"})
    )
    assert plan.blocked
    assert any(f.code == "DTDL_NESTED_COMPONENT" and f.blocking for f in plan.findings)
    with pytest.raises(ValueError, match="blocking"):
        build_parts(plan, "InvalidNestedComponent")


@pytest.mark.parametrize(
    "kind,code", [("Command", "COMMAND_RUNTIME"), ("Telemetry", "TELEMETRY_BINDING")]
)
def test_component_json_does_not_waive_runtime_requirements(write_models, kind, code):
    content = {"@type": kind, "name": "action"}
    if kind == "Telemetry":
        content["schema"] = "double"
    detail = interface(
        "Detail",
        [
            {"@type": "Property", "name": "label", "schema": "string"},
            content,
        ],
    )
    root = interface("Root", [{"@type": "Component", "name": "detail", "schema": detail["@id"]}])
    plan = make_plan(
        resolve(load(write_models(root, detail))),
        Options(compatibility=True, policies=frozenset({"component-properties", "json-objects"})),
    )
    assert any(f.code == code and f.blocking for f in plan.findings)
    assert any(f.code == "UNBOUND_STRUCT" and f.approved for f in plan.findings)
    with pytest.raises(ValueError, match="blocking"):
        build_parts(plan, "Blocked")


def test_object_json_does_not_skip_nested_metadata_analysis(write_models):
    root = interface(
        contents=[
            {
                "@type": "Property",
                "name": "position",
                "schema": {
                    "@type": "Object",
                    "fields": [
                        {
                            "name": "label",
                            "schema": "string",
                            "displayName": {"en": "Label", "fr": "Nom"},
                        }
                    ],
                },
            }
        ]
    )
    plan = make_plan(
        resolve(load(write_models(root))),
        Options(compatibility=True, policies=frozenset({"json-objects"})),
    )
    assert any(f.code == "METADATA_SEMANTICS" and f.blocking for f in plan.findings)
    assert plan.entities[root["@id"]].properties[0].pre_fallback_logical_type
