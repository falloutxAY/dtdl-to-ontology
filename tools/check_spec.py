"""Check every pinned normative DTDL v3 case; distinguish unsupported extensions."""

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

from dtdl_to_ontology.loader import load
from dtdl_to_ontology.resolver import resolve


def check(root: Path) -> dict:
    manifest = json.loads((root / "fixture.json").read_text(encoding="utf-8"))
    cases = []
    for relative, expected_hash in manifest["files"].items():
        data = (root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f"Fixture changed: {relative}")
        if relative.endswith(".json"):
            cases.extend(
                (relative, index, case)
                for index, case in enumerate(json.loads(data.decode("utf-8-sig")))
            )
    results = []
    for relative, index, case in cases:
        # Upstream input is a list of documents, each an object OR an array of objects.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for number, document in enumerate(case["input"]):
                (directory / f"{number}.json").write_text(json.dumps(document), encoding="utf-8")
            resolution = resolve(load(directory))
        findings = resolution.collection.findings + resolution.findings
        codes = sorted({f.code for f in findings})
        accepted = not any(f.blocking for f in findings)
        outcome = "matched" if accepted == case["valid"] else "disagreed"
        if (
            case["valid"]
            and not accepted
            and set(codes) <= {"UNKNOWN_EXTENSION", "CONTEXTUALLY_INCOMPLETE", "ENUM_VALUE"}
            and "UNKNOWN_EXTENSION" in codes
        ):
            outcome = "unsupported_extension"
        results.append(
            {
                "case": f"{Path(relative).name}:{index}",
                "expected_valid": case["valid"],
                "accepted": accepted,
                "outcome": outcome,
                "findings": codes,
            }
        )
    return {
        "repository": manifest["repository"],
        "revision": manifest["revision"],
        "cases": len(results),
        "counts": dict(sorted(Counter(r["outcome"] for r in results).items())),
        "differences": [r for r in results if r["outcome"] != "matched"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output already exists; choose a new evidence file.")
        result = check(args.fixture)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    except (OSError, ValueError, KeyError) as error:
        print(f"Specification check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"cases": result["cases"], **result["counts"]}))
    if result["cases"] != 6760 or result["counts"].get("unsupported_extension") != 97:
        print("Pinned corpus coverage changed; review the evidence baseline.", file=sys.stderr)
        return 1
    return int(bool(result["counts"].get("disagreed")))


if __name__ == "__main__":
    raise SystemExit(main())
