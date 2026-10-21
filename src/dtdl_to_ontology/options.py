"""Explicit approval boundaries for lossy projection policies."""

from dataclasses import dataclass, field
from pathlib import Path

from .loader import DTMI, MAX_FILE_BYTES, read_json
from .model import Finding, Source

POLICIES = frozenset(
    {
        "flatten-inheritance",
        "json-collections",
        "json-objects",
        "enum-underlying",
        "temporal-strings",
        "component-properties",
        "metadata-semantics",
        "reify-relationship-properties",
        "omit-relationships",
        "placeholder-targets",
    }
)


@dataclass(frozen=True)
class Options:
    compatibility: bool = False
    policies: frozenset[str] = frozenset()
    roots: tuple[str, ...] = ()
    omissions: frozenset[str] = frozenset()
    target_mappings: dict[str, str] = field(default_factory=dict)
    placeholders: frozenset[str] = frozenset()
    inheritance: bool = False
    source_revision: str | None = None

    def __post_init__(self) -> None:
        unknown = self.policies - POLICIES
        if unknown:
            raise ValueError(f"Unknown policies: {', '.join(sorted(unknown))}")
        if (
            self.policies or self.omissions or self.target_mappings or self.placeholders
        ) and not self.compatibility:
            raise ValueError("Loss policies and element mappings require --compatibility.")
        if self.omissions and "omit-relationships" not in self.policies:
            raise ValueError("Omissions require the omit-relationships policy.")
        if self.placeholders and "placeholder-targets" not in self.policies:
            raise ValueError("Placeholders require the placeholder-targets policy.")
        if self.inheritance and "flatten-inheritance" in self.policies:
            raise ValueError("Choose native inheritance or flatten-inheritance, not both.")
        for key in self.omissions | self.target_mappings.keys():
            identifier, separator, name = key.partition("/")
            if not separator or not name or "*" in name or not DTMI.fullmatch(identifier):
                raise ValueError(
                    f"Expected an exact DTMI/content-path relationship selector: {key}"
                )
        for identifier in (*self.roots, *self.placeholders, *self.target_mappings.values()):
            if not isinstance(identifier, str) or not DTMI.fullmatch(identifier):
                raise ValueError(f"Invalid configured DTMI: {identifier}")
        if self.omissions & self.target_mappings.keys():
            raise ValueError("A relationship cannot be both omitted and target-mapped.")

    def permits(self, policy: str) -> bool:
        return self.compatibility and policy in self.policies

    def loss(
        self,
        code: str,
        message: str,
        source: Source,
        owner: str,
        policy: str,
        workaround: str,
        limitation: str,
        selected: bool = True,
    ) -> Finding:
        return Finding(
            code,
            message,
            source,
            owner,
            fidelity="lossy",
            selected=selected,
            policy=policy,
            approved=self.permits(policy),
            workaround=workaround,
            limitation=limitation,
        )


def string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a string array.")
    return value


def load_options(
    config: Path | None = None,
    *,
    compatibility: bool = False,
    policies: list[str] | None = None,
    roots: list[str] | None = None,
    source_revision: str | None = None,
) -> Options:
    raw = {}
    if config is not None:
        with config.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Mapping configuration exceeds 16 MiB.")
        raw = read_json(data)
        if not isinstance(raw, dict):
            raise ValueError("Mapping configuration must be a JSON object.")
    allowed = {"policies", "omit_relationships", "target_mappings", "placeholders", "inheritance"}
    if unknown := raw.keys() - allowed:
        raise ValueError(f"Unknown mapping configuration fields: {sorted(unknown)}")
    mappings = raw.get("target_mappings", {})
    if not isinstance(mappings, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in mappings.items()
    ):
        raise ValueError("target_mappings must be a string-to-string object.")
    inheritance = raw.get("inheritance", False)
    if not isinstance(inheritance, bool):
        raise ValueError("inheritance must be a boolean target declaration.")
    return Options(
        compatibility=compatibility,
        policies=frozenset(string_list(raw.get("policies", []), "policies"))
        | frozenset(policies or []),
        roots=tuple(sorted(set(roots or []))),
        omissions=frozenset(string_list(raw.get("omit_relationships", []), "omit_relationships")),
        target_mappings=dict(sorted(mappings.items())),
        placeholders=frozenset(string_list(raw.get("placeholders", []), "placeholders")),
        inheritance=inheritance,
        source_revision=source_revision,
    )
