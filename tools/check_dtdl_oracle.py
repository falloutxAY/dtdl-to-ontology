"""Fail on unrecorded differences from the pinned independent parser."""

import json
import sys
from pathlib import Path

CORPUS = Path(__file__).parents[1] / "tests" / "fixtures" / "conformance" / "cases.json"
KNOWN_DIFFERENCES = {
    "annotation-missing-target": True,
    "mqtt-v3-recognition": False,
}


def check(results: dict) -> None:
    if results.get("parser") != "DTDLParser" or results.get("version") != "1.1.3":
        raise ValueError("Oracle identity/version does not match DTDLParser 1.1.3.")
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
    actual = results["cases"]
    by_id = {case["id"]: case for case in actual}
    if len(by_id) != len(actual) or set(by_id) != {case["id"] for case in cases}:
        raise ValueError("Oracle output has duplicate, missing, or unexpected cases.")
    mismatches = []
    for case in cases:
        expected = KNOWN_DIFFERENCES.get(case["id"], case["valid_source"])
        if by_id[case["id"]]["accepted"] is not expected:
            mismatches.append(case["id"])
    if mismatches:
        raise ValueError("Unrecorded parser differences: " + ", ".join(sorted(mismatches)))


def check_geospatial(results: dict) -> None:
    from dtdl_to_ontology.geo import GEOSCHEMAS

    expected = {term: definition["source_schema"] for term, definition in GEOSCHEMAS.items()}
    if results != expected:
        raise ValueError("Standard geometry shapes differ from the pinned independent parser.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(
            "Usage: check_dtdl_oracle.py <oracle-results.json> [geometry-results.json]"
        )
    check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig")))
    if len(sys.argv) == 3:
        check_geospatial(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig")))
    print("Pinned oracle results match every case, including documented differences.")
