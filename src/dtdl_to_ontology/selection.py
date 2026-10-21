"""Full inventory and explicit dependency closure, without implicit descendants."""

from collections import Counter, deque
from dataclasses import dataclass, field, replace

from .model import Finding, Source
from .resolver import Declaration, Reference, Resolution, types


def relationship_paths(
    resolution: Resolution,
    identifier: str,
    prefix: tuple[str, ...] = (),
    stack: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], Declaration]]:
    if identifier in stack or len(stack) >= 128:
        return []
    result = []
    for name, declaration in resolution.contents.get(identifier, {}).items():
        path = (*prefix, name)
        if "Relationship" in types(declaration.raw):
            result.append((path, declaration))
        elif "Component" in types(declaration.raw):
            target = declaration.raw.get("schema")
            if isinstance(target, str):
                result.extend(
                    relationship_paths(
                        resolution,
                        target,
                        path,
                        (*stack, identifier),
                    )
                )
    return result


@dataclass
class Selection:
    resolution: Resolution
    roots: list[str]
    selected: set[str]
    reasons: dict[str, list[dict]]
    omissions: set[str] = field(default_factory=set)
    target_mappings: dict[str, str] = field(default_factory=dict)
    placeholders: set[str] = field(default_factory=set)
    findings: list[Finding] = field(default_factory=list)

    def inventory(self) -> dict:
        models = self.resolution.collection.models
        counts: Counter = Counter()
        contexts: Counter = Counter()
        for model in models.values():
            contexts.update(model.contexts)
            pending = [model.raw]
            while pending:
                raw = pending.pop()
                if isinstance(raw, dict):
                    counts.update(types(raw))
                    pending.extend(raw.values())
                elif isinstance(raw, list):
                    pending.extend(raw)
        return {
            "interfaces": len(models),
            "declarations": dict(sorted(counts.items())),
            "contexts": dict(sorted(contexts.items())),
            "multiple_inheritance": sum(
                len(parents) > 1 for parents in self.resolution.parents.values()
            ),
            "selected": sorted(self.selected),
            "excluded": sorted(set(models) - self.selected),
            "roots": self.roots,
            "dependencies": dict(sorted(self.reasons.items())),
            "omissions": sorted(self.omissions),
            "placeholders": sorted(self.placeholders & self.selected),
        }


def select(
    resolution: Resolution,
    roots: list[str] | None = None,
    omissions: set[str] | None = None,
    target_mappings: dict[str, str] | None = None,
    placeholders: set[str] | None = None,
) -> Selection:
    models = resolution.collection.models
    roots = sorted(set(roots or models))
    result = Selection(
        resolution,
        roots,
        set(),
        {},
        omissions or set(),
        target_mappings or {},
        placeholders or set(),
    )
    references = {owner: set(entries) for owner, entries in resolution.references.items()}
    relationship_findings: list[Finding] = []
    known_relationships = set()
    for identifier in resolution.contents:
        for path, declaration in relationship_paths(resolution, identifier):
            name = "/".join(path)
            key = f"{identifier}/{name}"
            known_relationships.add(key)
            target = result.target_mappings.get(key, declaration.raw.get("target"))
            if key in result.omissions:
                relationship_findings.append(
                    Finding(
                        "RELATIONSHIP_OMITTED",
                        f"Explicitly omitted relationship: {key}",
                        declaration.source,
                        identifier,
                        fidelity="lossy",
                        policy="omit-relationships",
                        approved=True,
                        workaround="Supply accepted concrete endpoint mappings.",
                        limitation="The projected graph is incomplete.",
                    )
                )
                continue
            if not isinstance(target, str) or not target:
                relationship_findings.append(
                    Finding(
                        "UNTARGETED_RELATIONSHIP",
                        f"Relationship requires a concrete target: {key}",
                        declaration.source,
                        identifier,
                        workaround="Map a concrete target or explicitly omit this relationship.",
                        limitation="Fabric requires a concrete toEntity.",
                    )
                )
            elif target not in models and target not in result.placeholders:
                relationship_findings.append(
                    Finding(
                        "MISSING_TARGET",
                        f"By-reference relationship target is absent: {target}",
                        declaration.source,
                        identifier,
                        workaround="Provide the target, approve a placeholder, map, or omit.",
                        limitation=(
                            "By-reference targets need not invalidate DTDL; target unresolved."
                        ),
                    )
                )
            else:
                references.setdefault(identifier, set()).add(
                    Reference(target, f"relationship:{name}", declaration.source)
                )
    unknown = (result.omissions | set(result.target_mappings)) - known_relationships
    for key in sorted(unknown):
        result.findings.append(
            Finding(
                "SELECTION_CONFIG",
                f"Unknown relationship selection key: {key}",
                Source("<options>"),
            )
        )
    pending = deque((identifier, "root", None, Source("<options>")) for identifier in roots)
    while pending:
        identifier, reason, owner, source = pending.popleft()
        entry = {
            "reason": reason,
            "from": owner,
            "source": {"file": source.file, "pointer": source.pointer},
        }
        if entry not in result.reasons.setdefault(identifier, []):
            result.reasons[identifier].append(entry)
        if identifier in result.selected:
            continue
        if identifier not in models and identifier not in result.placeholders:
            result.findings.append(
                Finding(
                    "MISSING_SELECTION",
                    f"Unknown selected dependency: {identifier}",
                    source,
                    owner,
                )
            )
            continue
        result.selected.add(identifier)
        for reference in sorted(references.get(identifier, set())):
            pending.append((reference.target, reference.reason, identifier, reference.source))
    result.findings.extend(resolution.collection.findings)
    result.findings.extend(
        replace(finding, selected=finding.dtmi in result.selected)
        for finding in [*resolution.findings, *relationship_findings]
    )
    for identifier, reasons in result.reasons.items():
        result.reasons[identifier] = sorted(
            reasons,
            key=lambda value: (
                value["reason"],
                value["from"] or "",
                value["source"]["file"],
                value["source"]["pointer"],
            ),
        )
    return result
