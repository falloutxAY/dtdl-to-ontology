"""Selection-independent technical identities and TMDL text escaping."""

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass

LINEAGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/falloutxAY/dtdl-to-ontology")


def lineage(identity: str, role: str) -> str:
    return str(uuid.uuid5(LINEAGE_NAMESPACE, f"{role}:{identity}"))


def safe_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return sanitized or "unnamed"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class TargetName:
    namespace: str
    name: str
    lineage_tag: str

    @property
    def qualified(self) -> str:
        return f"{self.namespace}#{self.name}"


def target_name(identity: str, role: str = "entity") -> TargetName:
    base, _, suffix = identity.partition("/")
    body, _, version = base.removeprefix("dtmi:").partition(";")
    prefix, _, leaf = body.rpartition(":")
    namespace = "n_" + safe_name(prefix)[:72] + "__" + digest(prefix)
    name = safe_name(f"{leaf}_v{version}" + ("_" + suffix if suffix else ""))[:120]
    return TargetName(namespace, name + "__" + digest(identity), lineage(identity, role))


def quote(value: str) -> str:
    if not value or any(unicodedata.category(c) == "Cc" for c in value):
        raise ValueError("TMDL identifiers must be nonempty and contain no control characters.")
    return "'" + value.replace("'", "''") + "'"


def property_name(owner: str, name: str) -> str:
    return "p_" + safe_name(name)[:120] + "__" + digest(owner + "/" + name)


def doc_comments(value: str, indent: str = "") -> list[str]:
    return [f"{indent}/// {line}" for line in value.splitlines()] if value else []
