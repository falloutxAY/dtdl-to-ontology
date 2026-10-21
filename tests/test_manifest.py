from dtdl_to_ontology.loader import load
from dtdl_to_ontology.manifest import build_manifest
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve

from .conftest import interface


def test_complete_original_metadata_and_selection_remain_in_sidecar(write_models):
    source = interface(
        "Root",
        displayName={"en": "Root", "fr": "Racine"},
        comment="x" * 5000,
        schemas=[
            {
                "@id": "dtmi:example:E;1",
                "@type": "Enum",
                "valueSchema": "string",
                "enumValues": [{"name": "On", "enumValue": "on"}],
            }
        ],
    )
    excluded = interface("Excluded")
    collection = load(write_models(source, excluded))
    options = Options(roots=(source["@id"],), source_revision="as-supplied")
    plan = make_plan(resolve(collection), options)
    manifest = build_manifest(plan)
    assert manifest["source_models"][source["@id"]]["definition"] == source
    assert manifest["source_models"][excluded["@id"]]["definition"] == excluded
    assert not manifest["source_models"][excluded["@id"]]["selected"]
    assert manifest["source_revision_as_supplied"] == "as-supplied"
    assert manifest["source_files_sha256"] == collection.fingerprints
    assert manifest["target_entities"][source["@id"]]["name"]
    assert manifest["target_entities"][source["@id"]]["lineageTag"]
    assert len(manifest["source_models"][source["@id"]]["definition"]["comment"]) == 5000
    assert "parts" not in manifest
