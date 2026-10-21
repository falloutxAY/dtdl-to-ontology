"""Command-line interface."""

import argparse
import io
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .definition import build_parts
from .loader import load
from .manifest import build_manifest
from .options import load_options
from .plan import make_plan
from .preflight import preflight
from .publication import ensure_destination, publish
from .report import build_report, canonical_json, readable_report
from .resolver import resolve


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="dtdl-to-ontology",
        description="Analyze DTDLv3 and generate ontology-first Fabric TMDL without RDF.",
    )
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("analyze", "Inventory local DTDLv3 and report compatibility without deploying."),
        ("convert", "Generate an unbound Fabric definition; never deploy it."),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument(
            "input", type=Path, help="Local JSON collection file or model directory."
        )
        command.add_argument(
            "--root", action="append", default=[], help="Output root DTMI; repeatable."
        )
        command.add_argument(
            "--policy", action="append", default=[], help="Approve a named loss policy."
        )
        command.add_argument(
            "--compatibility", action="store_true", help="Enable named loss policies."
        )
        command.add_argument("--config", type=Path, help="Local JSON mapping configuration.")
        command.add_argument(
            "--source-revision", help="Source revision recorded as supplied, not proven."
        )
        command.add_argument("--json", action="store_true", help="Write a machine-readable report.")
        if name == "convert":
            command.add_argument(
                "--output", required=True, type=Path, help="New/empty output folder."
            )
            command.add_argument("--name", required=True, help="Ontology item display name.")
            command.add_argument("--logical-id", help="Explicit platform logical UUID.")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    published = False
    try:
        options = load_options(
            args.config,
            compatibility=args.compatibility,
            policies=args.policy,
            roots=args.root,
            source_revision=args.source_revision,
        )
        if args.command == "convert":
            ensure_destination(args.output)
            if not args.name.strip():
                raise ValueError("Ontology display name must not be empty.")
            if args.logical_id:
                uuid.UUID(args.logical_id)
        collection = load(args.input)
        plan = make_plan(resolve(collection), options)
        checks = preflight(plan, args.name if args.command == "convert" else "Ontology")
        plan.findings.extend(checks.findings)
        parts = None
        emission = "not_attempted"
        if args.command == "convert":
            emission = "blocked" if plan.blocked else "locally_validated"
            if not plan.blocked:
                parts = build_parts(plan, args.name, args.logical_id)
        report = build_report(plan.selection, plan.findings, plan.profile, emission)
        report["measurements"] = checks.measurements
        report["measurements_provisional"] = plan.blocked
        report["source_loading_complete"] = not collection.findings
        report["runtime_data_bindings"] = "not_generated"
        if args.command == "convert":
            publish(args.output, report, build_manifest(plan), parts)
            published = True
        print(canonical_json(report) if args.json else readable_report(report), end="")
        if args.command == "convert":
            return 1 if plan.blocked else 0
        return 1 if collection.findings else 0
    except (OSError, ValueError) as error:
        print(f"dtdl-to-ontology: {error}", file=sys.stderr)
        if published:
            print(
                f"Result was saved at {args.output}; console status output failed.", file=sys.stderr
            )
        elif args.json:
            print(
                canonical_json(
                    {
                        "analysis_status": "not_completed",
                        "emission_status": "not_published",
                        "service_acceptance": "unverified",
                        "error": str(error),
                    }
                ),
                end="",
            )
        return 2
