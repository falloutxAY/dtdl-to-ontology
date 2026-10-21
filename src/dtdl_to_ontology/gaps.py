"""Stable documentation categories shared by diagnostics and the gap catalog."""

GAP_CODES = {
    "inheritance": {"INHERITANCE", "NATIVE_MULTIPLE_INHERITANCE", "POLYMORPHISM"},
    "components": {"COMPONENT", "COMPONENT_CYCLE", "COMPONENT_RELATIONSHIP", "UNBOUND_STRUCT"},
    "collections-and-enums": {"COLLECTION", "ENUM_UNDERLYING"},
    "temporal-primitives": {"TEMPORAL_STRING"},
    "metadata-and-constraints": {"METADATA_SEMANTICS", "SOURCE_WIDTH", "WRITABLE"},
    "runtime-and-bindings": {"TELEMETRY_BINDING", "COMMAND_RUNTIME", "DATA_BINDINGS"},
    "relationships": {
        "RELATIONSHIP_PROPERTIES",
        "EDGE_ID_COLLISION",
        "UNTARGETED_RELATIONSHIP",
        "MISSING_TARGET",
        "TARGET_MAPPING",
        "PLACEHOLDER_TARGET",
        "PLACEHOLDER_CONFIG",
        "RELATIONSHIP_OMITTED",
        "UNBOUND_RELATIONSHIP",
    },
}


def documentation(code: str) -> str:
    section = "source-validation"
    if code.startswith("LIMIT_"):
        section = "capacity"
    else:
        for candidate, codes in GAP_CODES.items():
            if code in codes:
                section = candidate
                break
    return f"https://github.com/falloutxAY/dtdl-to-ontology/blob/main/docs/known-gaps.md#{section}"
