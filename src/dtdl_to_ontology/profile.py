"""Versioned limits from the Fabric new-experience definition contract."""

from dataclasses import asdict, dataclass

CONTRACT_URL = (
    "https://learn.microsoft.com/en-us/rest/api/fabric/articles/"
    "item-management/definitions/ontology-definition"
)


@dataclass(frozen=True)
class TargetProfile:
    id: str = "fabric-new-2026-10-20"
    source: str = CONTRACT_URL
    inheritance: bool = False
    unbound_relationships: bool = False
    relationship_evidence: str | None = None
    max_entities: int = 10_000
    max_relationships: int = 10_000
    max_properties: int = 1_000
    max_annotations: int = 100
    max_text: int = 4_000
    max_name: int = 512
    max_complex_depth: int = 32
    max_complex_nodes: int = 4_096
    max_struct_fields: int = 1_024
    max_document_nodes: int = 1_000_000
    max_document_depth: int = 160

    @property
    def relationships_enabled(self) -> bool:
        return self.unbound_relationships and bool(self.relationship_evidence)

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "relationship_mapping_enabled": self.relationships_enabled,
            "struct_backing_required": True,
            "struct_fallback_policy": "json-objects",
            "service_acceptance": "unverified",
        }


DEFAULT_PROFILE = TargetProfile(
    id="fabric-new-2026-11-09",
    unbound_relationships=True,
    relationship_evidence=(
        "https://github.com/falloutxAY/dtdl-to-ontology/blob/main/"
        "docs/fabric-acceptance.md#verified-definition-shapes"
    ),
)
