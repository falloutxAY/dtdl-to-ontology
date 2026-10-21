import json
import subprocess
import sys

import pytest

from dtdl_to_ontology.cli import _deployment_report, main

from .conftest import interface


def test_deploy_keeps_success_exit_for_reported_part_differences(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("FABRIC_ACCESS_TOKEN", "test-token")
    result = {
        "service_acceptance": "create_and_get_definition_succeeded",
        "semantic_equivalence": "not_asserted",
        "definition_part_paths_match": False,
        "definition_parts_textually_identical": False,
        "missing_part_paths": ["database.tmdl"],
        "additional_part_paths": [],
        "changed_part_paths": [],
    }
    monkeypatch.setattr("dtdl_to_ontology.cli.deploy_definition", lambda *args, **kwargs: result)

    exit_code = main(
        [
            "deploy",
            str(tmp_path / "definition.json"),
            "--workspace-id",
            "ec53121a-7764-4e63-aebb-7af2c46f9a66",
            "--json",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == result


def test_deployment_report_shows_part_comparison_without_semantic_claim():
    report = _deployment_report(
        {
            "create_operation_status": None,
            "get_definition_operation_status": None,
            "create_http_status": 201,
            "get_definition_http_status": 200,
            "display_name": "Example",
            "item_id": "item-id",
            "returned_part_count": 3,
            "expected_part_count": 3,
            "definition_part_paths_match": False,
            "definition_parts_textually_identical": False,
            "missing_part_paths": ["database.tmdl"],
            "additional_part_paths": [],
            "changed_part_paths": ["model.tmdl"],
            "semantic_equivalence": "not_asserted",
            "semantic_comparison": {
                "status": "completed",
                "supported_fields_match": False,
                "differences": {
                    "namespaces": {"missing": [], "additional": [], "changed": {}},
                    "entities": {"missing": [], "additional": [], "changed": {}},
                    "properties": {},
                    "relationships": {"missing": [], "additional": [], "changed": {}},
                },
            },
            "service_acceptance": "create_and_get_definition_succeeded",
        }
    )

    assert "Definition part paths match: no" in report
    assert "Decoded part text identical: no" in report
    assert "Missing part paths: database.tmdl" in report
    assert "Additional part paths: none" in report
    assert "Changed part paths: model.tmdl" in report
    assert "Normalized TMDL comparison: supported TMDL fields differ" in report
    assert "textual comparison is not semantic verification" in report
    assert "Service acceptance: create_and_get_definition_succeeded" in report


def test_deployment_report_labels_unsupported_semantic_comparison_unavailable():
    report = _deployment_report(
        {
            "create_operation_status": None,
            "get_definition_operation_status": None,
            "create_http_status": 201,
            "get_definition_http_status": 200,
            "display_name": "Example",
            "item_id": "item-id",
            "returned_part_count": 3,
            "expected_part_count": 3,
            "definition_part_paths_match": True,
            "definition_parts_textually_identical": True,
            "missing_part_paths": [],
            "additional_part_paths": [],
            "changed_part_paths": [],
            "semantic_comparison": {
                "status": "unsupported",
                "error": "Unsupported TMDL construct in entity.tmdl:2.",
            },
            "service_acceptance": "create_and_get_definition_succeeded",
        }
    )

    assert "Normalized TMDL comparison: unavailable" in report
    assert "Unsupported TMDL construct" in report
    assert "Service acceptance: create_and_get_definition_succeeded" in report


def test_installed_help():
    result = subprocess.run(
        [sys.executable, "-m", "dtdl_to_ontology", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "analyze" in result.stdout
    assert "convert" in result.stdout
    assert "deploy" in result.stdout


def test_import_and_version():
    from dtdl_to_ontology import __version__

    assert __version__


def test_deploy_requires_an_explicit_environment_token(write_models, tmp_path, monkeypatch):
    source = write_models(interface())
    output = tmp_path / "output"
    conversion = run_cli(
        "convert",
        source,
        "--name",
        "Example",
        "--output",
        output,
        "--json",
    )
    assert conversion.returncode == 0
    monkeypatch.delenv("FABRIC_ACCESS_TOKEN", raising=False)
    result = run_cli(
        "deploy",
        output / "definition.json",
        "--workspace-id",
        "ec53121a-7764-4e63-aebb-7af2c46f9a66",
        "--json",
    )
    assert result.returncode == 2
    assert "FABRIC_ACCESS_TOKEN" in result.stderr
    assert json.loads(result.stdout)["service_acceptance"] == "not_attempted"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "dtdl_to_ontology", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_analyze_and_convert_have_distinct_success_and_verification_states(write_models, tmp_path):
    source = write_models(interface())
    analysis = run_cli("analyze", source, "--json")
    assert analysis.returncode == 0
    assert json.loads(analysis.stdout)["emission_status"] == "not_attempted"
    destination = tmp_path / "output"
    conversion = run_cli("convert", source, "--name", "Example", "--output", destination, "--json")
    assert conversion.returncode == 0
    report = json.loads(conversion.stdout)
    assert report["emission_status"] == "locally_validated"
    assert report["service_acceptance"] == "unverified"
    assert (destination / "definition.json").exists()
    repeated = run_cli("convert", source, "--name", "Example", "--output", destination, "--json")
    assert repeated.returncode == 2
    assert "unchanged" in repeated.stderr
    assert json.loads(repeated.stdout)["emission_status"] == "not_published"


def test_blocked_convert_is_nonzero_with_diagnostics_only(write_models, tmp_path):
    source = write_models(
        interface(
            contents=[
                {
                    "@type": "Property",
                    "name": "values",
                    "schema": {"@type": "Array", "elementSchema": "string"},
                },
            ]
        )
    )
    destination = tmp_path / "blocked"
    result = run_cli(
        "convert",
        source,
        "--name",
        "Blocked",
        "--output",
        destination,
        "--compatibility",
        "--json",
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["analysis_status"] == "completed_with_findings"
    assert report["emission_status"] == "blocked"
    assert not report["selected_mapping_ready"]
    assert (destination / "report.json").exists()
    assert not (destination / "definition.json").exists()
    assert not (destination / "parts").exists()
    approved = run_cli(
        "convert",
        source,
        "--name",
        "Approved",
        "--output",
        tmp_path / "approved",
        "--compatibility",
        "--policy",
        "json-collections",
        "--json",
    )
    assert approved.returncode == 0


def test_telemetry_cli_requires_explicit_unbound_preservation_not_fake_ingestion(
    write_models,
    tmp_path,
):
    source = write_models(
        interface(
            contents=[
                {"@type": "Telemetry", "name": "reading", "schema": "double"},
            ]
        )
    )
    strict = run_cli(
        "convert",
        source,
        "--name",
        "Telemetry",
        "--output",
        tmp_path / "strict",
        "--json",
    )
    assert strict.returncode == 1
    finding = next(
        f for f in json.loads(strict.stdout)["findings"] if f["code"] == "TELEMETRY_BINDING"
    )
    assert finding["blocking"]
    assert "No definition-payload-only solution" in finding["limitation"]
    destination = tmp_path / "telemetry"
    approved = run_cli(
        "convert",
        source,
        "--name",
        "Telemetry",
        "--output",
        destination,
        "--compatibility",
        "--policy",
        "metadata-semantics",
        "--json",
    )
    assert approved.returncode == 0
    report = json.loads(approved.stdout)
    assert report["runtime_data_bindings"] == "not_generated"
    assert report["service_acceptance"] == "unverified"
    texts = "\n".join(
        path.read_text(encoding="utf-8") for path in (destination / "parts").rglob("*.tmdl")
    )
    assert "dataType: double" in texts
    assert "TimeSeries" not in texts and "backing" not in texts and "partition" not in texts


def test_command_cli_never_turns_metadata_preservation_into_execution(write_models, tmp_path):
    source = write_models(
        interface(
            contents=[
                {"@type": "Command", "name": "reboot"},
            ]
        )
    )
    destination = tmp_path / "command"
    result = run_cli(
        "convert",
        source,
        "--name",
        "Command",
        "--output",
        destination,
        "--compatibility",
        "--policy",
        "metadata-semantics",
        "--json",
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    finding = next(f for f in report["findings"] if f["code"] == "COMMAND_RUNTIME")
    assert finding["blocking"] and not finding["approved"]
    assert "no definition-payload-only solution" in finding["message"]
    assert report["runtime_data_bindings"] == "not_generated"
    assert not (destination / "definition.json").exists()


def test_json_stdout_is_utf8_for_non_ascii_source_locations(write_models):
    source = write_models(interface(contents=[{"@type": "Command", "name": "reboot"}]))
    source = source.rename(source.with_name("mod\u00e8les.json"))
    result = run_cli("analyze", source, "--json")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["findings"][0]["source"]["file"] == "mod\u00e8les.json"


def test_approved_enum_fallback_cannot_waive_invalid_source_literals(write_models, tmp_path):
    source = write_models(
        interface(
            contents=[
                {
                    "@type": "Property",
                    "name": "state",
                    "schema": {
                        "@type": "Enum",
                        "valueSchema": "string",
                        "enumValues": [{"name": "On", "enumValue": 1}],
                    },
                }
            ]
        )
    )
    destination = tmp_path / "invalid-enum"
    result = run_cli(
        "convert",
        source,
        "--name",
        "Invalid",
        "--output",
        destination,
        "--compatibility",
        "--policy",
        "enum-underlying",
        "--policy",
        "metadata-semantics",
        "--json",
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(f["code"] == "ENUM_VALUE" and f["blocking"] for f in report["findings"])
    assert (destination / "report.json").exists()
    assert not (destination / "definition.json").exists()


@pytest.mark.parametrize(
    "properties",
    [
        [{"@type": "Property", "name": "value", "schema": "string"}] * 2,
        [{"@type": "Telemetry", "name": "reading", "schema": "double"}],
    ],
)
def test_omitting_a_relationship_cannot_waive_invalid_source_state(
    write_models,
    tmp_path,
    properties,
):
    root = interface(
        contents=[
            {
                "@type": "Relationship",
                "name": "contains",
                "properties": properties,
            }
        ]
    )
    source = write_models(root)
    config = tmp_path / "omit.json"
    config.write_text(
        json.dumps(
            {
                "policies": ["omit-relationships", "metadata-semantics"],
                "omit_relationships": [root["@id"] + "/contains"],
            }
        ),
        encoding="utf-8",
    )
    destination = tmp_path / "invalid-edge"
    result = run_cli(
        "convert",
        source,
        "--name",
        "Invalid",
        "--output",
        destination,
        "--compatibility",
        "--config",
        config,
        "--json",
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(
        f["code"] in {"CONTENT_SHAPE", "CONTENT_TYPE"} and f["blocking"] for f in report["findings"]
    )
    assert any(f["code"] == "RELATIONSHIP_OMITTED" for f in report["findings"])
    assert (destination / "report.json").exists()
    assert not (destination / "definition.json").exists()


@pytest.mark.parametrize(
    "policies", [[], ["json-collections"], ["component-properties", "metadata-semantics"]]
)
def test_unbound_object_cli_is_diagnostic_only_without_specific_approval(
    write_models,
    tmp_path,
    policies,
):
    source = write_models(
        interface(
            contents=[
                {
                    "@type": "Property",
                    "name": "position",
                    "schema": {"@type": "Object", "fields": [{"name": "x", "schema": "double"}]},
                }
            ]
        )
    )
    destination = tmp_path / "blocked-object"
    flags = [flag for policy in policies for flag in ("--policy", policy)]
    result = run_cli(
        "convert",
        source,
        "--name",
        "Blocked",
        "--output",
        destination,
        "--compatibility",
        *flags,
        "--json",
    )
    assert result.returncode == 1
    finding = next(
        f for f in json.loads(result.stdout)["findings"] if f["code"] == "UNBOUND_STRUCT"
    )
    assert finding["blocking"] and finding["policy"] == "json-objects"
    assert (destination / "report.json").exists()
    assert not (destination / "definition.json").exists()
    assert not (destination / "parts").exists()


def test_json_object_cli_preserves_nested_source_blockers(write_models, tmp_path):
    source = write_models(
        interface(
            contents=[
                {
                    "@type": "Property",
                    "name": "details",
                    "schema": {
                        "@type": "Object",
                        "fields": [
                            {
                                "name": "state",
                                "schema": {
                                    "@type": "Enum",
                                    "valueSchema": "string",
                                    "enumValues": [{"name": "On", "enumValue": 1}],
                                },
                            }
                        ],
                    },
                }
            ]
        )
    )
    destination = tmp_path / "invalid-object"
    result = run_cli(
        "convert",
        source,
        "--name",
        "Invalid",
        "--output",
        destination,
        "--compatibility",
        "--policy",
        "json-objects",
        "--policy",
        "enum-underlying",
        "--json",
    )
    assert result.returncode == 1
    findings = json.loads(result.stdout)["findings"]
    assert any(f["code"] == "ENUM_VALUE" and f["blocking"] for f in findings)
    assert any(f["code"] == "UNBOUND_STRUCT" and f["approved"] for f in findings)
    assert not (destination / "definition.json").exists()
