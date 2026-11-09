import json
import re
from pathlib import Path

from dtdl_to_ontology.definition import build_parts
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.options import Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve

ROOT = Path(__file__).parents[1]


def test_public_document_links_resolve():
    for path in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            destination = target.partition("#")[0]
            assert (path.parent / destination).is_file(), (path, target)


def test_examples_still_match_recorded_accepted_definition_shapes():
    # This is a local drift check, not a new service acceptance run.
    record = json.loads((ROOT / "docs" / "evidence" / "2026-11-09.json").read_text())
    for case in record["cases"]:
        policies = frozenset(case["policies"])
        plan = make_plan(
            resolve(load(ROOT / case["source"])),
            Options(
                compatibility=bool(policies),
                policies=policies,
                inheritance=case.get("inheritance", False),
            ),
        )
        assert not plan.blocked
        assert len(plan.entities) == case["entities"]
        assert (
            sum(len(entity.properties) for entity in plan.entities.values()) == case["properties"]
        )
        assert len(plan.relationships) == case["relationships"]
        assert len(build_parts(plan, "AcceptanceShape")) == case["parts"]
