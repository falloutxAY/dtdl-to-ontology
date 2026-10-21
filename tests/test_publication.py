import builtins
import json
import sys
from pathlib import Path

import pytest

from dtdl_to_ontology.cli import main
from dtdl_to_ontology.definition import build_parts
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.manifest import build_manifest
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.publication import publish
from dtdl_to_ontology.report import build_report
from dtdl_to_ontology.resolver import resolve

from .conftest import interface


def test_atomic_success_and_rejection_of_a_previous_result(write_models, tmp_path):
    plan = make_plan(resolve(load(write_models(interface()))))
    report = build_report(plan.selection, plan.findings, emission="locally_validated")
    destination = tmp_path / "result"
    parts = build_parts(plan, "Example")
    publish(destination, report, build_manifest(plan), parts)
    original = (destination / "definition.json").read_bytes()
    with pytest.raises(ValueError, match="prior result is unchanged"):
        publish(destination, report, build_manifest(plan), parts)
    assert (destination / "definition.json").read_bytes() == original
    assert json.loads((destination / "report.json").read_text())["emission_status"] == (
        "locally_validated"
    )


def test_blocker_publishes_diagnostics_without_payload(write_models, tmp_path):
    plan = make_plan(
        resolve(
            load(
                write_models(
                    interface(
                        contents=[{"@type": "Command", "name": "reboot"}],
                    )
                )
            )
        )
    )
    report = build_report(plan.selection, plan.findings, emission="blocked")
    destination = tmp_path / "failed"
    publish(destination, report, build_manifest(plan), None)
    assert (destination / "report.json").exists()
    assert not (destination / "definition.json").exists()
    assert not (destination / "parts").exists()


def test_write_failure_never_leaks_a_partial_ready_result(write_models, tmp_path, monkeypatch):
    plan = make_plan(resolve(load(write_models(interface()))))
    report = build_report(plan.selection, plan.findings, emission="locally_validated")
    original = Path.write_text

    def fail_definition(path, *args, **kwargs):
        if path.name == "definition.json":
            raise OSError("simulated disk write failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_definition)
    destination = tmp_path / "failed"
    with pytest.raises(OSError, match="simulated"):
        publish(destination, report, build_manifest(plan), build_parts(plan, "Example"))
    assert not destination.exists()
    assert not list(tmp_path.glob(".failed.staging-*"))


def test_console_failure_after_publication_reports_that_result_was_saved(
    write_models,
    tmp_path,
    monkeypatch,
    capsys,
):
    source = write_models(interface())
    destination = tmp_path / "saved"
    original = builtins.print

    def fail_stdout(*args, **kwargs):
        if kwargs.get("file") is not sys.stderr:
            raise OSError("simulated console write failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", fail_stdout)
    result = main(
        [
            "convert",
            str(source),
            "--name",
            "Saved",
            "--output",
            str(destination),
            "--json",
        ]
    )
    assert result == 2
    assert (destination / "definition.json").exists()
    assert "Result was saved" in capsys.readouterr().err
