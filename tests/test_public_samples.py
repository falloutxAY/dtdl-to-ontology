import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve
from tools.fetch_samples import SOURCES, unpack

FIXTURE = Path(__file__).parents[1] / ".fixtures" / "parser"


def test_pinned_acquisition_checks_hash_and_keeps_license(tmp_path):
    source = dict(SOURCES["parser"])
    prefix = f"DTDLParser-{source['revision']}/"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(prefix + "LICENSE", "fixture license")
        archive.writestr(prefix + source["directory"] + "model.json", "{}")
    data = stream.getvalue()
    destination = tmp_path / "sample"
    with pytest.raises(ValueError, match="checksum"):
        unpack(data, destination, source)
    assert not destination.exists()
    source["sha256"] = hashlib.sha256(data).hexdigest()
    manifest = unpack(data, destination, source)
    assert (destination / "LICENSE").read_text() == "fixture license"
    assert len(manifest["files"]) == 2
    with pytest.raises(ValueError, match="already exists"):
        unpack(data, destination, source)


def test_independent_application_samples_keep_real_gaps():
    if not FIXTURE.exists():
        pytest.skip("Run python tools/fetch_samples.py parser .fixtures/parser")
    manifest = json.loads((FIXTURE / "fixture.json").read_text())
    assert manifest["revision"] == SOURCES["parser"]["revision"]
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == digest
    collection = load(FIXTURE / SOURCES["parser"]["directory"])
    resolution = resolve(collection)
    assert len(collection.models) == 6
    assert not collection.findings
    assert not resolution.findings
    plan = make_plan(resolution)
    assert {"MISSING_TARGET", "UNTARGETED_RELATIONSHIP", "EMPTY_STRUCT"} <= {
        f.code for f in plan.findings if f.blocking
    }
    projection = make_plan(
        resolution,
        Options(
            roots=("dtmi:com:example;1",),
            compatibility=True,
            policies=frozenset(
                {
                    "flatten-inheritance",
                    "component-properties",
                    "json-objects",
                    "metadata-semantics",
                }
            ),
        ),
    )
    assert not projection.blocked
    assert set(projection.entities) == {"dtmi:com:example;1", "dtmi:com:example:base;1"}
