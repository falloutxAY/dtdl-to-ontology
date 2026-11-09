"""Readable names, explicit conflict detection, and stable source-based lineage."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .model import Finding, Source

if TYPE_CHECKING:
    from .plan import Plan

NAME_KINDS = frozenset({"namespaces", "entities", "properties", "relationships"})
NameOverrides = dict[str, dict[str, str]]

LINEAGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/falloutxAY/dtdl-to-ontology")


def lineage(identity: str, role: str) -> str:
    return str(uuid.uuid5(LINEAGE_NAMESPACE, f"{role}:{identity}"))


def safe_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return sanitized or "unnamed"


def namespace_source(identity: str) -> str:
    body = identity.partition("/")[0].removeprefix("dtmi:").partition(";")[0]
    return body.rpartition(":")[0]


@dataclass(frozen=True)
class TargetName:
    namespace: str
    name: str
    lineage_tag: str

    @property
    def qualified(self) -> str:
        return f"{self.namespace}#{self.name}" if self.namespace else self.name


def target_name(
    identity: str, role: str = "entity", overrides: NameOverrides | None = None
) -> TargetName:
    overrides = overrides or {}
    base, _, suffix = identity.partition("/")
    body = base.removeprefix("dtmi:").partition(";")[0]
    prefix, _, leaf = body.rpartition(":")
    namespace = overrides.get("namespaces", {}).get(prefix, safe_name(prefix) if prefix else "")
    name = safe_name(leaf + ("_" + suffix if suffix else ""))
    category = "relationships" if role == "relationship" else "entities"
    name = overrides.get(category, {}).get(identity, name)
    return TargetName(namespace, name, lineage(identity, role))


def quote(value: str) -> str:
    if not value or any(unicodedata.category(c) == "Cc" for c in value):
        raise ValueError("TMDL identifiers must be nonempty and contain no control characters.")
    return "'" + value.replace("'", "''") + "'"


def annotation_text(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(unicodedata.category(char) == "Cc" for char in value)
    ):
        raise ValueError("Annotation values require nonempty, trimmed, single-line text.")
    return value


def property_name(owner: str, name: str, overrides: NameOverrides | None = None) -> str:
    return (overrides or {}).get("properties", {}).get(f"{owner}/{name}", safe_name(name))


def model_annotations(identity: str) -> dict[str, str]:
    model = identity.partition("/")[0]
    body, separator, version = model.removeprefix("dtmi:").partition(";")
    return {
        "dtdlModelId": model,
        "dtdlSourceName": body.rpartition(":")[2],
        **({"dtdlModelVersion": version} if separator else {}),
    }


@dataclass(frozen=True)
class NameConflict:
    category: str
    scope: str
    name: str
    keys: tuple[str, ...]
    source: Source
    owner: str

    def finding(self) -> Finding:
        return Finding(
            "NAME_CONFLICT",
            f"{self.category} name {self.name!r} in {self.scope} conflicts for "
            + ", ".join(self.keys),
            self.source,
            self.owner,
            workaround=(
                f"Set distinct names.{self.category} aliases for the listed source keys "
                "in --config, or use --interactive-names in a terminal."
            ),
            limitation="No hash, version suffix, truncation, or winning source is chosen.",
        )


def name_conflicts(plan: Plan) -> list[NameConflict]:
    groups: dict[tuple[str, str, str], dict[str, tuple[Source, str]]] = {}
    overrides = plan.options.name_overrides

    def add(category: str, scope: str, name: str, key: str, source: Source, owner: str) -> None:
        groups.setdefault((category, scope, name.casefold()), {})[key] = (source, owner)

    for identity, entity in sorted(plan.entities.items()):
        target = target_name(identity, overrides=overrides)
        if target.namespace:
            add(
                "namespaces",
                "ontology",
                target.namespace,
                namespace_source(identity),
                entity.source,
                identity,
            )
        add("entities", "ontology", target.qualified, identity, entity.source, identity)
        pending = [identity]
        seen = set()
        while pending:
            ancestor = pending.pop()
            if ancestor in seen or ancestor not in plan.entities:
                continue
            seen.add(ancestor)
            parent = plan.entities[ancestor]
            for prop in parent.properties:
                add(
                    "properties",
                    identity,
                    property_name(ancestor, prop.name, overrides),
                    f"{ancestor}/{prop.name}",
                    prop.source,
                    identity,
                )
            if parent.base:
                pending.append(parent.base)
    for relation in sorted(plan.relationships, key=lambda relation: relation.identity):
        target = target_name(relation.identity, "relationship", overrides)
        add(
            "relationships",
            "ontology",
            target.qualified,
            relation.identity,
            relation.source,
            relation.from_entity,
        )
    conflicts = []
    priority = {"namespaces": 0, "entities": 1, "properties": 2, "relationships": 3}
    for (category, scope, name), entries in sorted(
        groups.items(), key=lambda entry: (priority[entry[0][0]], *entry[0][1:])
    ):
        if len(entries) > 1:
            source, owner = next(iter(entries.values()))
            conflicts.append(
                NameConflict(category, scope, name, tuple(sorted(entries)), source, owner)
            )
    return conflicts


def naming_findings(plan: Plan) -> list[Finding]:
    findings = [conflict.finding() for conflict in name_conflicts(plan)]
    known = {
        "namespaces": {namespace_source(identity) for identity in plan.entities},
        "entities": set(plan.entities),
        "properties": {
            f"{identity}/{prop.name}"
            for identity, entity in plan.entities.items()
            for prop in entity.properties
        },
        "relationships": {relation.identity for relation in plan.relationships},
    }
    for category, entries in sorted(plan.options.name_overrides.items()):
        for key in sorted(entries.keys() - known[category]):
            findings.append(
                Finding(
                    "NAME_CONFIG",
                    f"Unknown selected {category} naming key: {key}",
                    Source("<configuration>", f"/names/{category}"),
                    workaround="Use an exact selected-output key or remove the stale alias.",
                )
            )
    for identity, entity in sorted(plan.entities.items()):
        target = target_name(identity, overrides=plan.options.name_overrides)
        if target.namespace.casefold() == "default":
            findings.append(
                Finding(
                    "NAME_CONFIG",
                    "The default namespace literal cannot be used as a namespace prefix.",
                    entity.source,
                    identity,
                    workaround="Choose a non-reserved alias in names.namespaces.",
                )
            )
        for value in (target.namespace, target.qualified):
            if len(value) > 250 or (
                re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", value, re.IGNORECASE)
            ):
                findings.append(
                    Finding(
                        "NAME_CONFIG",
                        f"Name {value!r} cannot be used as a portable definition filename.",
                        entity.source,
                        identity,
                        workaround="Choose a shorter, non-reserved explicit naming alias.",
                        limitation="The converter never silently truncates names.",
                    )
                )
    return findings


def doc_comments(value: str, indent: str = "") -> list[str]:
    return [f"{indent}/// {line}" for line in value.splitlines()] if value else []
