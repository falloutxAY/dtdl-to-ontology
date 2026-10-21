from dataclasses import replace

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.profile import DEFAULT_PROFILE
from dtdl_to_ontology.resolver import resolve

from .conftest import interface
from .test_selection import relationship


def test_explicit_target_mapping_keeps_unverified_gate(write_models):
    root, target = interface(), interface("Target")
    root["contents"] = [relationship()]
    key = root["@id"] + "/contains"
    options = Options(
        compatibility=True,
        roots=(root["@id"],),
        target_mappings={key: target["@id"]},
    )
    plan = make_plan(resolve(load(write_models(root, target))), options)
    assert any(f.code == "TARGET_MAPPING" and f.approved for f in plan.findings)
    assert any(f.code == "UNBOUND_RELATIONSHIP" and f.blocking for f in plan.findings)
    assert plan.blocked
    assert plan.relationships[0].to_entity == target["@id"]


def test_target_mapping_cannot_repair_an_invalid_source_dtmi(write_models):
    root = interface(contents=[relationship("not-a-dtmi")])
    target = interface("Target")
    options = Options(
        compatibility=True,
        target_mappings={root["@id"] + "/contains": target["@id"]},
    )
    profile = replace(
        DEFAULT_PROFILE,
        unbound_relationships=True,
        relationship_evidence="Synthetic test-only contract.",
    )
    plan = make_plan(resolve(load(write_models(root, target))), options, profile)
    assert any(f.code == "CONTENT_SHAPE" and f.blocking for f in plan.findings)
    assert any(f.code == "TARGET_MAPPING" and f.approved for f in plan.findings)
    assert plan.blocked


def test_placeholder_is_visible_and_cannot_bypass_gate(write_models):
    missing = "dtmi:example:Absent;1"
    root = interface(contents=[relationship(missing)])
    options = Options(
        compatibility=True,
        policies=frozenset({"placeholder-targets"}),
        placeholders=frozenset({missing}),
    )
    plan = make_plan(resolve(load(write_models(root))), options)
    assert plan.entities[missing].placeholder
    assert "unavailable" in plan.entities[missing].description
    assert any(f.code == "PLACEHOLDER_TARGET" for f in plan.findings)
    assert plan.blocked


def test_confirmed_internal_profile_plans_concrete_endpoints(write_models):
    target = interface("Target")
    root = interface(contents=[relationship(target["@id"])])
    profile = replace(
        DEFAULT_PROFILE,
        unbound_relationships=True,
        relationship_evidence="Synthetic contract evidence for unit tests only.",
    )
    plan = make_plan(resolve(load(write_models(root, target))), profile=profile)
    assert not plan.blocked
    assert plan.relationships[0].from_entity == root["@id"]


def test_edge_reification_preserves_properties_and_endpoint_roles(write_models):
    target = interface("Target")
    edge = relationship(target["@id"])
    edge["properties"] = [{"@type": "Property", "name": "substance", "schema": "string"}]
    root = interface(contents=[edge])
    options = Options(
        compatibility=True,
        policies=frozenset({"reify-relationship-properties"}),
    )
    resolution = resolve(load(write_models(root, target)))
    blocked = make_plan(resolution, options)
    assert any(f.code == "UNBOUND_RELATIONSHIP" and f.blocking for f in blocked.findings)
    confirmed = replace(
        DEFAULT_PROFILE,
        unbound_relationships=True,
        relationship_evidence="Synthetic contract evidence for unit tests only.",
    )
    plan = make_plan(resolution, options, confirmed)
    assert not plan.blocked
    entity = plan.entities[root["@id"] + "/contains#edge"]
    substance = next(p for p in entity.properties if p.name == "substance")
    assert substance.logical_type == {"kind": "primitive", "dataType": "string"}
    assert substance.original == edge["properties"][0]
    assert {r.to_entity for r in plan.relationships} == {root["@id"], target["@id"]}
    assert all(r.from_entity == entity.identity for r in plan.relationships)
    assert (
        entity.identity
        == make_plan(resolution, options, confirmed).entities[entity.identity].identity
    )
