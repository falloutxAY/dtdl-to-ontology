from dtdl_to_ontology.loader import load
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.selection import select

from .conftest import interface


def relationship(target=None):
    raw = {"@type": "Relationship", "name": "contains"}
    if target:
        raw["target"] = target
    return raw


def test_inventory_and_bounded_closure_are_separate(write_models):
    base = interface("Base")
    target = interface("Target")
    root = interface("Root", [relationship(target["@id"])], extends=base["@id"])
    other = interface("Other")
    selected = select(resolve(load(write_models(root, base, target, other))), [root["@id"]])
    assert selected.selected == {root["@id"], base["@id"], target["@id"]}
    assert selected.inventory()["interfaces"] == 4
    assert selected.inventory()["excluded"] == [other["@id"]]
    assert any(e["reason"] == "extends" for e in selected.reasons[base["@id"]])


def test_explicit_omission_does_not_include_target(write_models):
    target = interface("Target")
    root = interface("Root", [relationship(target["@id"])])
    key = root["@id"] + "/contains"
    selected = select(resolve(load(write_models(root, target))), [root["@id"]], omissions={key})
    assert selected.selected == {root["@id"]}
    assert selected.inventory()["omissions"] == [key]
    assert any(f.code == "RELATIONSHIP_OMITTED" and f.approved for f in selected.findings)


def test_missing_by_reference_target_is_not_missing_component(write_models):
    root = interface(contents=[relationship("dtmi:example:Absent;1")])
    selected = select(resolve(load(write_models(root))))
    assert {f.code for f in selected.findings} == {"MISSING_TARGET"}
    assert "need not invalidate DTDL" in selected.findings[0].limitation


def test_unselected_findings_remain_visible_without_blocking(write_models):
    root = interface("Root")
    other = interface("Other", [relationship()])
    selected = select(resolve(load(write_models(root, other))), [root["@id"]])
    finding = next(f for f in selected.findings if f.code == "UNTARGETED_RELATIONSHIP")
    assert not finding.selected
    assert not finding.blocking


def test_target_mapping_and_placeholder_require_explicit_input(write_models):
    root = interface(contents=[relationship()])
    target = "dtmi:example:ExplicitPlaceholder;1"
    key = root["@id"] + "/contains"
    selection = select(
        resolve(load(write_models(root))),
        [root["@id"]],
        target_mappings={key: target},
        placeholders={target},
    )
    assert selection.selected == {root["@id"], target}
    assert selection.inventory()["placeholders"] == [target]
    assert not selection.findings


def test_unknown_root_and_omission_are_errors(write_models):
    selection = select(
        resolve(load(write_models(interface()))),
        ["dtmi:example:Absent;1"],
        omissions={"unknown/contains"},
    )
    assert {f.code for f in selection.findings} == {"MISSING_SELECTION", "SELECTION_CONFIG"}
