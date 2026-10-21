from pathlib import Path

from dtdl_to_ontology.gaps import GAP_CODES, documentation


def test_all_finding_categories_link_to_existing_catalog_sections():
    catalog = (Path(__file__).parents[1] / "docs" / "known-gaps.md").read_text()
    anchors = {
        line.removeprefix("## ").lower().replace(" ", "-")
        for line in catalog.splitlines()
        if line.startswith("## ")
    }
    for code in ["JSON", "LIMIT_ENTITIES", *sum((list(v) for v in GAP_CODES.values()), [])]:
        assert documentation(code).partition("#")[2] in anchors
