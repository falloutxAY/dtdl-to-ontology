import base64
import json

import pytest

from dtdl_to_ontology.definition import build_parts, envelope, write_parts
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve

from .conftest import interface


def test_complete_definition_decodes_exactly_to_readable_utf8_parts(write_models, tmp_path):
    root = interface(description="Un équipement")
    plan = make_plan(resolve(load(write_models(root))))
    parts = build_parts(plan, "Ontology")
    assert {".platform", "database.tmdl", "model.tmdl", "namespaces/default.tmdl"} <= parts.keys()
    assert "compatibilityLevel: 1000000" in parts["database.tmdl"]
    assert "ref namespace default" in parts["model.tmdl"]
    platform = json.loads(parts[".platform"])
    assert platform["config"]["version"] == "2.0"
    assert platform["metadata"]["type"] == "Ontology"
    write_parts(parts, tmp_path / "parts")
    payload = envelope(parts)
    for part in payload["parts"]:
        assert part["payloadType"] == "InlineBase64"
        assert "\\" not in part["path"]
        decoded = base64.b64decode(part["payload"], validate=True).decode("utf-8")
        assert decoded == parts[part["path"]]
        assert (tmp_path / "parts").joinpath(*part["path"].split("/")).read_bytes() == (
            decoded.encode("utf-8")
        )
    assert parts == build_parts(plan, "Ontology")
    assert not any(path.startswith(("tables/", "reports/")) for path in parts)
    assert not {"manifest.json", "report.json"} & parts.keys()


def test_blockers_cannot_be_packaged_as_a_ready_definition(write_models):
    root = interface(contents=[{"@type": "Command", "name": "reboot"}])
    plan = make_plan(resolve(load(write_models(root))), Options(compatibility=True))
    with pytest.raises(ValueError, match="blocking"):
        build_parts(plan, "Blocked")
