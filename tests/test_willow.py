import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from dtdl_to_ontology.definition import build_parts, envelope
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.manifest import build_manifest
from dtdl_to_ontology.options import POLICIES, Options, load_options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.preflight import preflight
from dtdl_to_ontology.report import build_report, canonical_json
from dtdl_to_ontology.resolver import resolve, types

REVISION = "1d19b2584df02e05714628a57a7ddd69edeef29c"
FIXTURE = Path(__file__).parents[1] / ".fixtures" / "willow"


@pytest.fixture(scope="module")
def willow():
    if not (FIXTURE / "Ontology").exists():
        pytest.skip(
            "Acquire the pinned fixture explicitly: python tools\\fetch_willow.py .fixtures\\willow"
        )
    metadata = json.loads((FIXTURE / "fixture.json").read_text())
    assert metadata["revision"] == REVISION
    collection = load(FIXTURE / "Ontology")
    expected = {
        name.removeprefix("Ontology/"): sha
        for name, sha in metadata["files"].items()
        if name.startswith("Ontology/")
    }
    assert collection.fingerprints == expected
    assert not collection.findings
    assert not any(name.startswith("Metadata/") for name in collection.fingerprints)
    return resolve(collection)


def test_full_pinned_inventory_and_strict_blockers_are_not_conversion_success(willow):
    plan = make_plan(willow)
    inventory = plan.selection.inventory()
    assert inventory["interfaces"] == 3705
    assert len(plan.selection.selected) == inventory["interfaces"]
    assert not inventory["excluded"]
    assert inventory["multiple_inheritance"] == 225
    expected = {
        "Property": 1384,
        "Relationship": 111,
        "Component": 62,
        "Object": 69,
        "Array": 16,
        "Map": 49,
        "Enum": 166,
        "ValueAnnotation": 388,
        "Override": 362,
    }
    assert {key: inventory["declarations"][key] for key in expected} == expected
    assert not {"Telemetry", "Command"} & inventory["declarations"].keys()
    assert inventory["contexts"]["dtmi:dtdl:extension:quantitativeTypes;1"] == 173
    assert any(
        f.code == "MISSING_TARGET" and "LeaseContract" in f.message and f.blocking
        for f in plan.findings
    )
    assert any(
        f.code == "ANNOTATION_TARGET" and f.dtmi == "dtmi:com:willowinc:WaterLeakEvent;1"
        for f in plan.findings
    )
    checks = preflight(plan)
    assert "LIMIT_RELATIONSHIPS" in {f.code for f in checks.findings}
    assert len(plan.relationships) == 14744  # Concrete, non-attributed strict candidates only.
    report = build_report(plan.selection, plan.findings + checks.findings)
    assert len(report["findings"]) == len(plan.findings) + len(checks.findings)
    assert Counter(f["code"] for f in report["findings"])["MISSING_TARGET"] == 1
    assert report["blockers"] > 0
    assert report["emission_status"] == "not_attempted"
    assert report["service_acceptance"] == "unverified"
    assert plan.blocked
    assert len(plan.entities) == 3705
    assert len(plan.relationships) == 14744


def test_full_pinned_policy_sweep_keeps_nonwaivable_gaps_and_limits(willow):
    plan = make_plan(willow, Options(compatibility=True, policies=POLICIES))
    checks = preflight(plan, "WillowPolicySweep")
    findings = [*plan.findings, *checks.findings]

    assert plan.selection.selected == set(willow.collection.models)
    assert not plan.selection.inventory()["excluded"]
    assert len(plan.entities) == 3723
    assert len(plan.relationships) == 14780
    assert plan.blocked
    assert not any(f.code == "UNBOUND_RELATIONSHIP" for f in findings)
    assert Counter(f.code for f in willow.findings) == {
        "EXTENSION_TYPE": 5,
        "ANNOTATION_TARGET": 1,
        "OVERRIDE_FIELD": 1,
    }
    assert {finding.code for finding in checks.findings if finding.blocking} == {
        "LIMIT_RELATIONSHIPS",
        "LIMIT_DOCUMENT_NODES",
    }
    assert checks.measurements["document_nodes"] > plan.profile.max_document_nodes
    blocked_owners = {
        identifier
        for identifier in willow.collection.models
        if any(f.blocking and f.dtmi == identifier for f in findings)
    }
    assert "dtmi:com:willowinc:WaterLeakEvent;1" in blocked_owners
    assert any(f.code == "MISSING_TARGET" and f.blocking for f in findings)
    assert any(f.code == "ANNOTATION_TARGET" and f.blocking for f in findings)


def test_bounded_building_projection_is_complete_explicit_and_deterministic(willow):
    options = load_options(
        Path(__file__).parents[1] / "examples" / "willow-building.json",
        compatibility=True,
        roots=["dtmi:com:willowinc:Building;1"],
        source_revision=REVISION,
    )
    rejected = make_plan(willow, replace(options, policies=options.policies - {"json-objects"}))
    unbound = [f for f in rejected.findings if f.code == "UNBOUND_STRUCT"]
    assert len(unbound) == 15 and all(f.blocking for f in unbound)
    with pytest.raises(ValueError, match="blocking"):
        build_parts(rejected, "Rejected")
    plan = make_plan(willow, options)
    checks = preflight(plan, "WillowBuilding")
    assert not plan.blocked
    assert not checks.findings
    expected = {
        f"dtmi:com:willowinc:{name};1"
        for name in (
            "Address",
            "Building",
            "Component",
            "Space",
            "SpaceArea",
            "SpaceCapacity",
            "SpaceComponent",
            "TimeZone",
            "UtilityEmissionFactor",
            "UtilityRate",
        )
    }
    assert plan.selection.selected == expected
    assert len(plan.selection.inventory()["excluded"]) == 3695
    assert checks.measurements["entities"] == 10
    assert checks.measurements["relationships"] == 0
    assert max(checks.measurements["properties_per_entity"].values()) == 37
    assert sum(checks.measurements["properties_per_entity"].values()) == 79
    fallbacks = [f for f in plan.findings if f.code == "UNBOUND_STRUCT"]
    assert len(fallbacks) == 15 and all(f.approved for f in fallbacks)
    assert (
        sum(
            prop.pre_fallback_logical_type is not None
            for entity in plan.entities.values()
            for prop in entity.properties
        )
        == 15
    )
    omissions = [f for f in plan.findings if f.code == "RELATIONSHIP_OMITTED" and f.selected]
    assert len(omissions) == 22
    assert all(f.approved and not f.blocking for f in omissions)
    constructs = set()
    pending = [willow.collection.models[identifier].raw for identifier in expected]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            constructs.update(types(item))
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    assert {"Object", "Array", "Map", "Enum", "Component", "Area"} <= constructs
    parts = build_parts(plan, "WillowBuilding")
    assert len(parts) == 15
    assert "namespaces/com_willowinc.tmdl" in parts
    building = parts["entities/com_willowinc#Building.tmdl"]
    assert "\tproperty 'height'" in building
    assert "annotation 'dtdlModelVersion' = 1\n" in building
    assert "annotation 'dtdlValueEncoding' = json\n" in building
    assert "entityRelationships.tmdl" not in parts
    assert not any("baseEntityType" in text for text in parts.values())
    assert not any("complexDataType" in text for text in parts.values())
    reordered = resolve(
        replace(
            willow.collection,
            models=dict(reversed(list(willow.collection.models.items()))),
        )
    )
    second = make_plan(reordered, options)
    assert envelope(parts) == envelope(build_parts(second, "WillowBuilding"))
    first_manifest = build_manifest(plan)
    assert first_manifest["selection"]["selected"] == sorted(expected)
    assert canonical_json(first_manifest) == canonical_json(build_manifest(second))
    assert canonical_json(build_report(plan.selection, plan.findings)) == canonical_json(
        build_report(second.selection, second.findings)
    )
