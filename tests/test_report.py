import json

import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.model import Finding, Source
from dtdl_to_ontology.report import build_report, canonical_json, readable_report
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.selection import select

from .conftest import interface
from .test_selection import relationship


def test_json_and_readable_report_explain_same_source_failure(write_models):
    source = interface(contents=[relationship("dtmi:example:Absent;1")])
    report = build_report(select(resolve(load(write_models(source)))))
    machine = json.loads(canonical_json(report))
    human = readable_report(report)
    finding = machine["findings"][0]
    assert finding["code"] == "MISSING_TARGET"
    assert finding["dtmi"] == source["@id"]
    assert finding["source"]["pointer"] == "/0/contents/0"
    assert finding["code"] in human
    assert finding["message"] in human
    assert finding["workaround"] in human
    assert finding["limitation"] in human
    assert machine["blockers"] == 1
    assert not machine["selected_mapping_ready"]
    assert machine["emission_status"] == "not_attempted"
    assert machine["service_acceptance"] == "unverified"
    assert machine["summary"]["affected_selected_model_count"] == 1
    assert machine["summary"]["blocking_causes"][0]["code"] == finding["code"]


def test_summary_counts_occurrences_without_conflating_models_or_approvals(write_models):
    a, b, excluded = (interface(name) for name in ("A", "B", "Excluded"))
    selection = select(resolve(load(write_models(a, b, excluded))), roots=[a["@id"], b["@id"]])
    collection = Finding(
        "COLLECTION",
        "Collection projection.",
        Source("models.json", "/0/contents/0"),
        a["@id"],
        policy="json-collections",
        workaround="Review the loss | preserve originals.\nChoose explicitly.",
    )
    findings = [
        collection,
        collection,
        Finding(
            "COLLECTION",
            "Another collection.",
            Source("models.json", "/1/contents/0"),
            b["@id"],
            policy="json-collections",
        ),
        Finding(
            "SOURCE_WIDTH", "Width.", Source("models.json"), a["@id"], policy="metadata-semantics"
        ),
        Finding(
            "METADATA_SEMANTICS",
            "Units.",
            Source("models.json"),
            a["@id"],
            policy="metadata-semantics",
        ),
        Finding(
            "LIMIT_RELATIONSHIPS",
            "Measured 10001; supported limit is 10000.",
            Source("<target>"),
        ),
        Finding("MISSING_TARGET", "Absent target.", Source("models.json"), b["@id"]),
        Finding(
            "ENUM_UNDERLYING",
            "Approved enum.",
            Source("models.json"),
            a["@id"],
            policy="enum-underlying",
            approved=True,
        ),
        Finding("NOTICE", "Warning.", Source("models.json"), a["@id"], severity="warning"),
        Finding(
            "UNBOUND_STRUCT",
            "Excluded object.",
            Source("models.json"),
            excluded["@id"],
            selected=False,
            policy="json-objects",
        ),
    ]
    report = build_report(selection, findings)
    summary = report["summary"]
    assert report["blockers"] == 7
    assert len(report["findings"]) == 10
    assert summary["affected_selected_model_count"] == 2
    assert summary["blocking_findings_without_selected_model"] == 1
    assert summary["selected_nonblocking_findings"] == 2
    assert summary["unselected_findings"] == 1
    assert summary["policies_requiring_review"] == ["json-collections", "metadata-semantics"]
    assert sum(cause["finding_count"] for cause in summary["blocking_causes"]) == 7
    cause = summary["blocking_causes"][0]
    assert cause["code"] == "COLLECTION"
    assert cause["finding_count"] == 3
    assert cause["affected_model_count"] == 2
    assert cause["model_examples"] == [a["@id"], b["@id"]]
    assert {finding["code"] for finding in report["findings"]} >= {
        "ENUM_UNDERLYING",
        "NOTICE",
        "UNBOUND_STRUCT",
    }
    human = readable_report(report)
    overview = human.partition("## Findings")[0]
    assert "Counts are finding occurrences, not distinct source defects" in overview
    assert "### Policy decisions" in overview
    assert "Compatibility mode alone approves nothing" in overview
    assert "### Target-limit failures" in overview
    assert "Measured 10001; supported limit is 10000." in overview
    assert "Review the loss \\| preserve originals.\\nChoose explicitly." in overview
    assert canonical_json(report) == canonical_json(build_report(selection, findings[::-1]))


def test_summary_keeps_policy_groups_distinct_and_bounds_examples(write_models):
    models = [interface(f"Model{index}") for index in range(5)]
    selection = select(resolve(load(write_models(*models))))
    findings = [
        Finding(
            "LIMIT_PROPERTIES",
            f"Measured {1001 + index}; supported limit is 1000.",
            Source("models.json", f"/{index}"),
            model["@id"],
        )
        for index, model in enumerate(models)
    ]
    findings.extend(
        Finding(
            "PROJECTION",
            "Choose a projection.",
            Source("models.json"),
            models[0]["@id"],
            policy=policy,
        )
        for policy in ("json-collections", "json-objects")
    )
    report = build_report(selection, findings)
    causes = report["summary"]["blocking_causes"]
    assert len(causes) == 3
    limit = causes[0]
    assert limit["finding_count"] == limit["affected_model_count"] == 5
    assert limit["model_examples"] == [model["@id"] for model in models[:3]]
    assert len(limit["examples"]) == 3
    assert len(report["findings"]) == 7
    assert [cause["policy"] for cause in causes[1:]] == ["json-collections", "json-objects"]
    report["measurements_provisional"] = True
    overview = readable_report(report).partition("## Findings")[0]
    assert "2 more LIMIT_PROPERTIES findings below." in overview
    assert "Measurements are provisional while mapping blockers remain." in overview


@pytest.mark.parametrize("with_findings", [False, True])
def test_summary_without_blockers_does_not_hide_approved_or_unselected_findings(
    write_models, with_findings
):
    selection = select(resolve(load(write_models(interface()))))
    findings = (
        [
            Finding(
                "COLLECTION",
                "Approved collection.",
                Source("models.json"),
                "dtmi:example:Example;1",
                policy="json-collections",
                approved=True,
            ),
            Finding("SOURCE", "Excluded source.", Source("other.json"), selected=False),
        ]
        if with_findings
        else []
    )
    report = build_report(selection, findings)
    assert report["selected_mapping_ready"]
    assert report["summary"]["blocking_causes"] == []
    assert report["summary"]["policies_requiring_review"] == []
    assert report["summary"]["selected_nonblocking_findings"] == int(with_findings)
    assert report["summary"]["unselected_findings"] == int(with_findings)
    human = readable_report(report)
    assert "No blockers for the selected projection" in human
    assert "### Policy decisions" not in human
    assert "### Target-limit failures" not in human
    for finding in findings:
        assert finding.message in human
    del report["summary"]
    assert readable_report(report) == human
