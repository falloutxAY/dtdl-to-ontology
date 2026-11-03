import json
from pathlib import Path

import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.model import Finding, Source
from dtdl_to_ontology.options import POLICIES, Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve
from tools.check_dtdl_oracle import KNOWN_DIFFERENCES, check, check_geospatial

CORPUS_PATH = Path(__file__).parent / "fixtures" / "conformance" / "cases.json"
CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_declared_features_have_positive_and_negative_models():
    cases = CORPUS["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    declared = set(CORPUS["features"])
    assert {feature for case in cases for feature in case["features"]} == declared
    for feature in declared:
        assert {case["valid_source"] for case in cases if feature in case["features"]} == {
            True,
            False,
        }


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["id"])
def test_source_conformance_models(case, tmp_path):
    path = tmp_path / (case["id"] + ".json")
    path.write_text(json.dumps(case["model"]), encoding="utf-8")
    resolution = resolve(load(path))
    findings = resolution.collection.findings + resolution.findings
    if case["valid_source"]:
        assert not findings
    else:
        assert set(case["findings"]) <= {f.code for f in findings}
        assert make_plan(resolution, Options(compatibility=True, policies=POLICIES)).blocked
    plan = make_plan(resolution)
    for finding in plan.findings:
        assert finding.code and finding.source.file
        record = finding.to_dict()
        assert record["fidelity"] and record["workaround"] and record["limitation"]
        assert record["documentation"]


def test_diagnostics_have_nonempty_source_and_fidelity_contract():
    # Also covers diagnostics that do not occur in the bounded fixture corpus.
    record = Finding("CUSTOM", "Example", Source("model.json", "/contents/0")).to_dict()
    assert record["source"]["pointer"] == "/contents/0"
    assert record["fidelity"] == "unsupported"
    assert record["blocking"]


def oracle_results():
    return {
        "parser": "DTDLParser",
        "version": "1.1.3",
        "cases": [
            {"id": case["id"], "accepted": KNOWN_DIFFERENCES.get(case["id"], case["valid_source"])}
            for case in CORPUS["cases"]
        ],
    }


def test_oracle_comparison_requires_exact_coverage_and_no_new_disagreements():
    results = oracle_results()
    check(results)
    results["cases"][0]["accepted"] = not results["cases"][0]["accepted"]
    with pytest.raises(ValueError, match="Unrecorded"):
        check(results)
    results = oracle_results()
    results["cases"].pop()
    with pytest.raises(ValueError, match="missing"):
        check(results)
    results = oracle_results()
    results["cases"].append(results["cases"][0])
    with pytest.raises(ValueError, match="duplicate"):
        check(results)


def test_geometry_oracle_comparison_detects_missing_or_changed_standard_shapes():
    from dtdl_to_ontology.geo import GEOSCHEMAS

    expected = {term: definition["source_schema"] for term, definition in GEOSCHEMAS.items()}
    check_geospatial(expected)
    with pytest.raises(ValueError, match="geometry shapes"):
        check_geospatial({**expected, "point": {}})
