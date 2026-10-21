import json

from dtdl_to_ontology.loader import load
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
