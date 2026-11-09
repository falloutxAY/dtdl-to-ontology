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


def summarize_findings(findings: list[dict], selected: set[str]) -> dict:
    blocking = [finding for finding in findings if finding["blocking"]]
    groups: dict[tuple[str, str | None], list[dict]] = {}
    for finding in blocking:
        groups.setdefault((finding["code"], finding["policy"]), []).append(finding)

    def models(entries: list[dict]) -> list[str]:
        return sorted({entry["dtmi"] for entry in entries if entry["dtmi"] in selected})

    causes = []
    for (code, policy), entries in groups.items():
        affected = models(entries)
        causes.append(
            {
                "code": code,
                "policy": policy,
                "finding_count": len(entries),
                "affected_model_count": len(affected),
                "model_examples": affected[:3],
                "actions": sorted({entry["workaround"] for entry in entries}),
                "examples": entries[:3],
            }
        )
    causes.sort(key=lambda cause: (-cause["finding_count"], cause["code"], cause["policy"] or ""))
    return {
        "affected_selected_model_count": len(models(blocking)),
        "blocking_findings_without_selected_model": sum(
            finding["dtmi"] not in selected for finding in blocking
        ),
        "selected_nonblocking_findings": sum(
            finding["selected"] and not finding["blocking"] for finding in findings
        ),
        "unselected_findings": sum(not finding["selected"] for finding in findings),
        "blocking_causes": causes,
        "policies_requiring_review": sorted(
            {finding["policy"] for finding in blocking if finding["policy"]}
        ),
    }


def build_report(
    selection: Selection,
    findings: list[Finding] | None = None,
    profile: TargetProfile = DEFAULT_PROFILE,
    emission: str = "not_attempted",
) -> dict:
    ordered = ordered_findings(selection.findings if findings is None else findings)
    blockers = sum(finding.blocking for finding in ordered)
    records = [finding.to_dict() for finding in ordered]
    return {
        "schema_version": 1,
        "analysis_status": "completed_with_findings" if ordered else "completed",
        "emission_status": emission,
        "selected_mapping_ready": blockers == 0,
        "blockers": blockers,
        "target_profile": profile.to_dict(),
        "service_acceptance": "unverified",
        "inventory": selection.inventory(),
        "summary": summarize_findings(records, selection.selected),
        "findings": records,
    }


def text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", "\\r").replace("\n", "\\n")


def readable_report(report: dict) -> str:
    inventory = report["inventory"]
    summary = (
        report["summary"]
        if "summary" in report
        else summarize_findings(report["findings"], set(inventory["selected"]))
    )
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
        "## Action summary",
        "",
        f"Selected models with blockers: {summary['affected_selected_model_count']}",
        "Blocking findings without a selected model ID: "
        f"{summary['blocking_findings_without_selected_model']}",
        f"Selected non-blocking findings: {summary['selected_nonblocking_findings']}",
        f"Unselected findings: {summary['unselected_findings']}",
        "",
        "Counts are finding occurrences, not distinct source defects. "
        "Causes and affected models can overlap; examples show at most three per cause.",
        "",
    ]
    if summary["blocking_causes"]:
        lines.extend(
            [
                "| Blocking cause | Findings | Selected models (examples) | Next action |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for cause in summary["blocking_causes"]:
            label = cause["code"]
            if cause["policy"]:
                label += f" ({cause['policy']})"
            models = str(cause["affected_model_count"])
            if cause["model_examples"]:
                models += ": " + ", ".join(cause["model_examples"])
                if cause["affected_model_count"] > len(cause["model_examples"]):
                    models += ", ..."
            actions = "; ".join(cause["actions"])
            lines.append(
                f"| {text(label)} | {cause['finding_count']} | {text(models)} | {text(actions)} |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "No blockers for the selected projection. "
                "Non-blocking and unselected findings remain below.",
                "",
            ]
        )
    if summary["policies_requiring_review"]:
        lines.extend(
            [
                "### Policy decisions",
                "",
                "Review losses before explicitly approving: "
                + ", ".join(f"`{text(policy)}`" for policy in summary["policies_requiring_review"])
                + ". Compatibility mode alone approves nothing; "
                "policies do not waive invalid source.",
                "",
            ]
        )
    limits = [cause for cause in summary["blocking_causes"] if cause["code"].startswith("LIMIT_")]
    if limits:
        lines.extend(["### Target-limit failures", ""])
        if report.get("measurements_provisional"):
            lines.extend(["Measurements are provisional while mapping blockers remain.", ""])
        for cause in limits:
            for example in cause["examples"]:
                source = example["source"]
                location = source["file"] + "#" + source["pointer"]
                lines.append(
                    f"- {text(cause['code'])}: {text(example['message'])} ({text(location)})."
                )
            extra = cause["finding_count"] - len(cause["examples"])
            if extra:
                lines.append(f"- {extra} more {text(cause['code'])} findings below.")
        lines.append("")
    lines.extend(["## Findings", ""])
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
