"""Command-line interface."""

import argparse
import io
import os
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .definition import build_parts
from .fabric import FabricApiError, deploy_definition
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
        description="Analyze, convert, or optionally deploy DTDLv3 to Fabric Ontology.",
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
    deploy = commands.add_parser(
        "deploy",
        help="Create an Ontology from a local definition and retrieve its service definition.",
    )
    deploy.add_argument("definition", type=Path, help="Locally validated definition.json file.")
    deploy.add_argument("--workspace-id", required=True, help="Target Fabric workspace UUID.")
    deploy.add_argument(
        "--folder-id", help="Optional target Fabric folder UUID; omitted means workspace root."
    )
    deploy.add_argument(
        "--name",
        help="Optional item name; when supplied it must match the definition's .platform name.",
    )
    deploy.add_argument(
        "--token-env",
        default="FABRIC_ACCESS_TOKEN",
        help="Environment variable containing a Fabric access token.",
    )
    deploy.add_argument("--json", action="store_true", help="Write a machine-readable result.")
    return result


def _deployment_report(result: dict) -> str:
    operation = result["create_operation_status"] or "not required"
    get_operation = result["get_definition_operation_status"] or "not required"

    def paths_or_none(paths: list[str]) -> str:
        return ", ".join(paths) if paths else "none"

    return (
        "# Fabric deployment check\n\n"
        f"Create: HTTP {result['create_http_status']} ({operation})\n"
        f"Get definition: HTTP {result['get_definition_http_status']} ({get_operation})\n"
        f"Item: {result['display_name']} ({result['item_id']})\n"
        f"Returned parts: {result['returned_part_count']} "
        f"(expected {result['expected_part_count']})\n"
        "Definition part paths match: "
        f"{'yes' if result['definition_part_paths_match'] else 'no'}\n"
        "Decoded part text identical: "
        f"{'yes' if result['definition_parts_textually_identical'] else 'no'}\n"
        f"Missing part paths: {paths_or_none(result['missing_part_paths'])}\n"
        f"Additional part paths: {paths_or_none(result['additional_part_paths'])}\n"
        f"Changed part paths: {paths_or_none(result['changed_part_paths'])}\n"
        "Semantic equivalence: not asserted; textual comparison is not semantic verification.\n"
        f"Service acceptance: {result['service_acceptance']}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    published = False
    try:
        if args.command == "deploy":
            token = os.environ.get(args.token_env)
            if not token:
                raise ValueError(
                    f"No Fabric access token found in environment variable {args.token_env!r}."
                )
            result = deploy_definition(
                args.definition,
                args.workspace_id,
                token,
                expected_name=args.name,
                folder_id=args.folder_id,
            )
            print(
                canonical_json(result) if args.json else _deployment_report(result),
                end="",
            )
            return 0
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
    except FabricApiError as error:
        print(f"dtdl-to-ontology: {error}", file=sys.stderr)
        if args.json:
            print(
                canonical_json({"service_acceptance": "failed", "error": str(error)}),
                end="",
            )
        return 3
    except (OSError, ValueError) as error:
        print(f"dtdl-to-ontology: {error}", file=sys.stderr)
        if published:
            print(
                f"Result was saved at {args.output}; console status output failed.", file=sys.stderr
            )
        elif args.json:
            failure = (
                {"service_acceptance": "not_attempted", "error": str(error)}
                if args.command == "deploy"
                else {
                    "analysis_status": "not_completed",
                    "emission_status": "not_published",
                    "service_acceptance": "unverified",
                    "error": str(error),
                }
            )
            print(canonical_json(failure), end="")
        return 2
