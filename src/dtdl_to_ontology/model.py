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

    @property
    def contexts(self) -> tuple[str, ...]:
        context = self.raw.get("@context", [])
        return tuple([context] if isinstance(context, str) else context)


@dataclass
class Collection:
    models: dict[str, Model] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    fingerprints: dict[str, str] = field(default_factory=dict)
