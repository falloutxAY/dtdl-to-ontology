"""Source provenance and diagnostics shared by the compiler stages."""

from dataclasses import asdict, dataclass, field
from typing import Any

from .gaps import documentation


@dataclass(frozen=True, order=True)
class Source:
    file: str
    pointer: str = ""

    def child(self, *parts: str | int) -> "Source":
        escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
        return Source(self.file, self.pointer + "/" + "/".join(escaped))


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    source: Source
    dtmi: str | None = None
    fidelity: str = "unsupported"
    severity: str = "error"
    selected: bool = True
    policy: str | None = None
    approved: bool = False
    workaround: str = "Correct the source or select a supported projection."
    limitation: str = "No target mapping has been established."

    @property
    def blocking(self) -> bool:
        return self.selected and self.severity == "error" and not self.approved

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "blocking": self.blocking,
            "documentation": documentation(self.code),
        }


@dataclass
class Model:
    id: str
    raw: dict[str, Any]
    source: Source
    sources: list[Source] = field(default_factory=list)
    original: dict[str, Any] | None = None

    @property
    def contexts(self) -> tuple[str, ...]:
        context = self.raw.get("@context", [])
        return tuple([context] if isinstance(context, str) else context)


@dataclass
class Collection:
    models: dict[str, Model] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    fingerprints: dict[str, str] = field(default_factory=dict)
    active_contexts: dict[Source, tuple[str, ...]] = field(default_factory=dict)
    element_sources: dict[int, Source] = field(default_factory=dict)
    original_elements: dict[int, dict] = field(default_factory=dict)
    member_sources: dict[tuple[int, str], Source] = field(default_factory=dict)
    normalization: list[dict] = field(default_factory=list)
    interface_bytes: dict[Source, int] = field(default_factory=dict)

    def location(self, raw: dict, fallback: Source, member: str | None = None) -> Source:
        if member is not None:
            return self.member_sources.get(
                (id(raw), member), self.element_sources.get(id(raw), fallback).child(member)
            )
        return self.element_sources.get(id(raw), fallback)

    def contexts_at(self, source: Source) -> tuple[str, ...]:
        pointer = source.pointer
        while True:
            location = Source(source.file, pointer)
            if location in self.active_contexts:
                return self.active_contexts[location]
            if not pointer:
                return ()
            pointer = pointer.rpartition("/")[0]
