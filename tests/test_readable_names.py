import json
from dataclasses import replace

import pytest

from dtdl_to_ontology.cli import main
from dtdl_to_ontology.definition import build_parts
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.manifest import build_manifest
from dtdl_to_ontology.naming import lineage, model_annotations, name_conflicts, target_name
from dtdl_to_ontology.options import Options, load_options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.preflight import logical_document, preflight
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.semantic import parse_tmdl
from dtdl_to_ontology.tmdl import render_relationships

from .conftest import interface
from .test_cli import run_cli


def plan_for(path, names=None, **kwargs):
    return make_plan(resolve(load(path)), Options(name_overrides=names or {}, **kwargs))


@pytest.mark.parametrize(
    "left,right,category",
    [
        ("dtmi:example:Sensor;1", "dtmi:example:Sensor;2", "entities"),
        ("dtmi:example:Sensor;1", "dtmi:example:sensor;1", "entities"),
        ("dtmi:a_b:Sensor;1", "dtmi:a:b:Other;1", "namespaces"),
    ],
)
def test_readable_collisions_block_without_picking_a_winner(write_models, left, right, category):
    models = [interface(**{"@id": identifier}) for identifier in (left, right)]
    plan = plan_for(write_models(*models))
    conflicts = name_conflicts(plan)
    assert category in {c.category for c in conflicts}
    checks = preflight(plan)
    assert "NAME_CONFLICT" in {f.code for f in checks.findings}
    with pytest.raises(ValueError, match="naming conflicts"):
        build_parts(plan, "Blocked")


def test_exact_aliases_update_definition_manifest_and_preflight_consistently(write_models):
    base = interface("Sensor")
    child = interface(
        "Current",
        extends=base["@id"],
        contents=[{"@type": "Property", "name": "reading", "schema": "double"}],
    )
    target = interface("Target")
    child["contents"].append({"@type": "Relationship", "name": "contains", "target": target["@id"]})
    names = {
        "namespaces": {"example": "Buildings"},
        "entities": {base["@id"]: "Equipment", child["@id"]: "Sensor"},
        "properties": {child["@id"] + "/reading": "temperature"},
        "relationships": {child["@id"] + "/contains": "Sensor_contains"},
    }
    plan = plan_for(write_models(base, child, target), names, inheritance=True)
    assert not preflight(plan).findings
    parts = build_parts(plan, "Readable")
    parsed = parse_tmdl(parts)
    entity = parsed["entities"]["Buildings#Sensor"]
    assert entity["baseEntityType"] == "Buildings#Equipment"
    assert entity["lineageTag"] == lineage(child["@id"], "entity")
    prop = entity["properties"]["temperature"]
    assert prop["annotations"]["dtdlSourceName"] == "reading"
    assert prop["lineageTag"] == lineage(child["@id"] + "/reading", "property")
    relation = parsed["relationships"]["Buildings#Sensor_contains"]
    assert relation["fromEntity"] == "Buildings#Sensor"
    assert relation["toEntity"] == "Buildings#Target"
    assert relation["label"] == "contains"
    assert "\tlabel: contains\n" in parts["entityRelationships.tmdl"]
    assert parsed["namespaces"]["Buildings"]["annotations"]["dtdlNamespace"] == "example"
    manifest = build_manifest(plan)
    assert manifest["target_entities"][child["@id"]]["name"] == "Buildings#Sensor"
    assert (
        manifest["target_entities"][child["@id"]]["properties"][0]["target_name"] == "temperature"
    )
    document = logical_document(plan, "Readable")
    assert {e["name"] for e in document["model"]["entities"]} == set(parsed["entities"])
    assert document["model"]["entityRelationships"][0]["label"] == "contains"


@pytest.mark.parametrize("version", ["1", "3.17", ""])
def test_model_version_is_metadata_not_the_visible_name(write_models, version):
    identifier = "dtmi:example:Settings" + (";" + version if version else "")
    plan = plan_for(write_models(interface(**{"@id": identifier})))
    record = parse_tmdl(build_parts(plan, "Metadata"))["entities"]["example#Settings"]
    assert record["annotations"]["dtdlModelId"] == identifier
    if version:
        assert record["annotations"]["dtdlModelVersion"] == version
    else:
        assert "dtdlModelVersion" not in record["annotations"]


def test_case_conflicts_include_inherited_property_scopes(write_models):
    base = interface("Base", [{"@type": "Property", "name": "Value", "schema": "string"}])
    child = interface(
        "Child", [{"@type": "Property", "name": "value", "schema": "string"}], extends=base["@id"]
    )
    path = write_models(base, child)
    plan = plan_for(path, inheritance=True)
    conflict = next(c for c in name_conflicts(plan) if c.category == "properties")
    assert set(conflict.keys) == {base["@id"] + "/Value", child["@id"] + "/value"}
    fixed = plan_for(
        path, {"properties": {child["@id"] + "/value": "localValue"}}, inheritance=True
    )
    assert not preflight(fixed).findings


def test_native_inherited_provenance_keeps_the_declaring_model_version(write_models):
    base = interface("Base", [{"@type": "Property", "name": "name", "schema": "string"}])
    child = interface("Child", extends=base["@id"], **{"@id": "dtmi:example:Child;2"})
    plan = plan_for(write_models(base, child), inheritance=True)
    parsed = parse_tmdl(build_parts(plan, "Origins"))
    assert parsed["entities"]["example#Child"]["annotations"]["dtdlModelVersion"] == "2"
    annotations = parsed["entities"]["example#Base"]["properties"]["name"]["annotations"]
    assert annotations["dtdlModelId"] == base["@id"]
    assert annotations["dtdlModelVersion"] == "1"


def test_relation_conflicts_and_aliases_are_checked(write_models):
    first = interface(
        "Sensor", [{"@type": "Relationship", "name": "contains", "target": "dtmi:example:Target;1"}]
    )
    second = interface(
        "Other", [{"@type": "Relationship", "name": "contains", "target": "dtmi:example:Target;1"}]
    )
    target = interface("Target")
    path = write_models(first, second, target)
    names = {
        "relationships": {
            first["@id"] + "/contains": "contains",
            second["@id"] + "/contains": "Contains",
        }
    }
    assert any(c.category == "relationships" for c in name_conflicts(plan_for(path, names)))
    names["relationships"][second["@id"] + "/contains"] = "otherContains"
    assert not preflight(plan_for(path, names)).findings


@pytest.mark.parametrize("category", ["entities", "properties", "namespaces", "relationships"])
def test_unknown_alias_keys_are_diagnostics_not_silent_ignores(write_models, category):
    plan = plan_for(write_models(interface()), {category: {"typo": "Readable"}})
    assert "NAME_CONFIG" in {f.code for f in preflight(plan).findings}
    with pytest.raises(ValueError, match="aliases"):
        build_parts(plan, "Blocked")


@pytest.mark.parametrize(
    "names",
    [
        {"invalid": {}},
        {"entities": []},
        {"entities": {"key": "../escape"}},
        {"entities": {"key": ""}},
        {"namespaces": {"example": "default"}},
    ],
)
def test_invalid_alias_configuration_is_rejected(names):
    with pytest.raises(ValueError):
        Options(name_overrides=names)


def test_noninteractive_conflicts_publish_diagnostics_only(write_models, tmp_path):
    source = write_models(interface(), interface(**{"@id": "dtmi:example:Example;2"}))
    output = tmp_path / "conflict"
    result = run_cli("convert", source, "--name", "Blocked", "--output", output, "--json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(f["code"] == "NAME_CONFLICT" for f in report["findings"])
    assert not (output / "definition.json").exists()
    assert not (output / "parts").exists()
    config = tmp_path / "names.json"
    config.write_text(json.dumps({"names": {"entities": {"dtmi:example:Example;2": "Current"}}}))
    converted = run_cli(
        "convert",
        source,
        "--name",
        "Fixed",
        "--output",
        tmp_path / "fixed",
        "--config",
        config,
        "--json",
    )
    assert converted.returncode == 0
    assert load_options(tmp_path / "fixed" / "naming.json").name_overrides == {
        "entities": {"dtmi:example:Example;2": "Current"}
    }


def test_interactive_resolution_is_explicit_and_saved(write_models, tmp_path, monkeypatch, capsys):
    source = write_models(interface(), interface(**{"@id": "dtmi:example:Example;2"}))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    responses = iter(["OldSettings", "CurrentSettings"])
    monkeypatch.setattr("builtins.input", lambda: next(responses))
    output = tmp_path / "interactive"
    assert (
        main(
            [
                "convert",
                str(source),
                "--name",
                "Names",
                "--output",
                str(output),
                "--interactive-names",
            ]
        )
        == 0
    )
    assert "Name for names.entities" in capsys.readouterr().err
    names = load_options(output / "naming.json").name_overrides["entities"]
    assert set(names.values()) == {"OldSettings", "CurrentSettings"}
    assert (output / "definition.json").exists()


def test_json_or_redirected_runs_cannot_prompt(write_models, tmp_path):
    source = write_models(interface())
    result = run_cli(
        "convert",
        source,
        "--name",
        "NoPrompt",
        "--output",
        tmp_path / "none",
        "--interactive-names",
        "--json",
    )
    assert result.returncode == 2
    assert "requires a terminal" in result.stderr
    assert not (tmp_path / "none").exists()


def test_interactive_flag_does_not_prompt_without_a_conflict(
    write_models, tmp_path, monkeypatch, capsys
):
    source = write_models(interface())
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda: pytest.fail("No conflict: must not prompt"))
    assert (
        main(
            [
                "convert",
                str(source),
                "--name",
                "Clear",
                "--output",
                str(tmp_path / "clear"),
                "--interactive-names",
            ]
        )
        == 0
    )
    capsys.readouterr()


def test_interactive_cancellation_does_not_publish(write_models, tmp_path, monkeypatch, capsys):
    source = write_models(interface(), interface(**{"@id": "dtmi:example:Example;2"}))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda: "")
    output = tmp_path / "cancelled"
    assert (
        main(
            [
                "convert",
                str(source),
                "--name",
                "Cancelled",
                "--output",
                str(output),
                "--interactive-names",
            ]
        )
        == 2
    )
    assert "cancelled" in capsys.readouterr().err
    assert not output.exists()


def test_default_namespace_and_nontruncating_name_limits(write_models):
    plan = plan_for(write_models(interface(**{"@id": "dtmi:Settings;1"})))
    assert target_name("dtmi:Settings;1").qualified == "Settings"
    assert "entities/Settings.tmdl" in build_parts(plan, "Default")
    long_name = "A" * 251
    renamed = replace(plan.options, name_overrides={"entities": {"dtmi:Settings;1": long_name}})
    plan.options = renamed
    assert target_name("dtmi:Settings;1", overrides=renamed.name_overrides).name == long_name
    assert "NAME_CONFIG" in {f.code for f in preflight(plan).findings}


def test_annotation_helper_keeps_source_identity():
    assert model_annotations("dtmi:example:Sensor;1/feeds#edge")["dtdlModelId"] == (
        "dtmi:example:Sensor;1"
    )


def test_relationship_labels_cannot_inject_tmdl(write_models):
    root = interface(
        contents=[{"@type": "Relationship", "name": "contains", "target": "dtmi:example:Example;1"}]
    )
    plan = plan_for(write_models(root))
    plan.relationships[0].label = "contains\nentity injected"
    with pytest.raises(ValueError, match="programming names"):
        render_relationships(plan)


@pytest.mark.parametrize("value", ["", " leading", "trailing ", "line\ninjected", "tab\tvalue"])
def test_annotation_text_is_explicitly_validated(write_models, value):
    plan = plan_for(write_models(interface()))
    next(iter(plan.entities.values())).annotations["custom"] = value
    assert "ANNOTATION_TEXT" in {f.code for f in preflight(plan).findings}


def test_named_collection_metadata_identifies_json_encoding(write_models):
    identifier = "dtmi:example:Strings;1"
    root = interface(
        contents=[{"@type": "Property", "name": "tags", "schema": identifier}],
        schemas=[{"@type": "Array", "@id": identifier, "elementSchema": "string"}],
    )
    plan = make_plan(
        resolve(load(write_models(root))),
        Options(compatibility=True, policies=frozenset({"json-collections"})),
    )
    parsed = parse_tmdl(build_parts(plan, "NamedSchema"))
    annotation = parsed["entities"]["example#Example"]["properties"]["tags"]["annotations"]
    assert annotation["dtdlValueEncoding"] == "json"
