"""Deterministic machine-readable and human-readable compatibility reports."""

import json

from .model import Finding
from .profile import DEFAULT_PROFILE, TargetProfile
from .selection import Selection


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def ordered_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (
            f.dtmi or "",
            f.source.file,
            f.source.pointer,
            f.code,
            f.message,
            f.policy or "",
        ),
    )


def build_report(
    selection: Selection,
    findings: list[Finding] | None = None,
    profile: TargetProfile = DEFAULT_PROFILE,
    emission: str = "not_attempted",
) -> dict:
    ordered = ordered_findings(selection.findings if findings is None else findings)
    blockers = sum(finding.blocking for finding in ordered)
    return {
        "schema_version": 1,
        "analysis_status": "completed_with_findings" if ordered else "completed",
        "emission_status": emission,
        "selected_mapping_ready": blockers == 0,
        "blockers": blockers,
        "target_profile": profile.to_dict(),
        "service_acceptance": "unverified",
        "inventory": selection.inventory(),
        "findings": [finding.to_dict() for finding in ordered],
    }


def text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", "\\r").replace("\n", "\\n")


def readable_report(report: dict) -> str:
    inventory = report["inventory"]
    lines = [
        "# Conversion compatibility report",
        "",
        f"Analysis: {report['analysis_status']}",
        f"Emission: {report['emission_status']}",
        f"Selected mapping ready: {report['selected_mapping_ready']}",
        f"Blocking findings: {report['blockers']}",
        "Fabric service acceptance: unverified",
        "",
        f"Input interfaces: {inventory['interfaces']}",
        f"Selected definitions: {len(inventory['selected'])}",
        f"Excluded definitions: {len(inventory['excluded'])}",
        "",
        "## Findings",
        "",
    ]
    for finding in report["findings"]:
        source = finding["source"]
        location = source["file"] + "#" + source["pointer"]
        lines.extend(
            [
                f"### {text(finding['code'])}: {text(finding['dtmi'] or '<input>')}",
                f"- Source: {text(location)}",
                f"- Fidelity: {finding['fidelity']}; severity: {finding['severity']}; "
                f"selected: {finding['selected']}; blocking: {finding['blocking']}",
                f"- Finding: {text(finding['message'])}",
                f"- Workaround: {text(finding['workaround'])}",
                f"- Remaining limitation: {text(finding['limitation'])}",
                f"- Policy: {text(finding['policy'])}; approved: {finding['approved']}",
                f"- Documentation: {finding['documentation']}",
                "",
            ]
        )
    if not report["findings"]:
        lines.append("No local compatibility findings. Service acceptance remains unverified.")
    return "\n".join(lines) + "\n"
