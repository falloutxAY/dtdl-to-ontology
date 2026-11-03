"""Per-material DTDL source rules, never waived by target loss policies."""

from .model import Collection, Finding
from .normalization import MATERIALS
from .source_graph import Element, types
from .vocabulary import EXTENSIONS, QUANTITY_UNITS

COMMON = {"@id", "@type", "@context", "comment", "description", "displayName"}
REQUIRED = {
    "Interface": {"@id"},
    "Property": {"name", "schema"},
    "Telemetry": {"name", "schema"},
    "Command": {"name"},
    "Component": {"name", "schema"},
    "Relationship": {"name"},
    "Array": {"elementSchema"},
    "Enum": {"valueSchema"},
    "Map": {"mapKey", "mapValue"},
    "Object": set(),
    "Field": {"name", "schema"},
    "MapKey": {"name", "schema"},
    "MapValue": {"name", "schema"},
    "CommandRequest": {"name", "schema"},
    "CommandResponse": {"name", "schema"},
    "EnumValue": {"name", "enumValue"},
}
OPTIONAL = {
    "Interface": {"contents", "extends", "schemas"},
    "Property": {"writable"},
    "Telemetry": set(),
    "Command": {"commandType", "request", "response"},
    "Component": set(),
    "Relationship": {"writable", "target", "properties", "minMultiplicity", "maxMultiplicity"},
    "Array": set(),
    "Enum": {"enumValues"},
    "Map": set(),
    "Object": {"fields"},
    "Field": set(),
    "MapKey": set(),
    "MapValue": set(),
    "CommandRequest": set(),
    "CommandResponse": set(),
    "EnumValue": set(),
}
INFERRED = {"Field", "MapKey", "MapValue", "CommandRequest", "CommandResponse", "EnumValue"}


def validate_material(
    element: Element, collection: Collection, extension_members: dict[str, set[str]]
) -> list[Finding]:
    import re

    raw, source, owner = element.raw, element.source, element.owner
    findings = []

    def issue(code: str, message: str, member: str) -> None:
        findings.append(Finding(code, message, collection.location(raw, source, member), owner))

    materials = types(raw) & MATERIALS
    if len(materials) != 1:
        issue("MATERIAL_TYPE", "Exactly one material type is required.", "@type")
        return findings
    kind = next(iter(materials))
    contexts = collection.active_contexts.get(source, ())
    version2 = "dtmi:dtdl:context;2" in contexts
    for member in REQUIRED[kind] - raw.keys():
        issue("REQUIRED_MEMBER", f"{kind} requires {member}.", member)
    allowed = COMMON | REQUIRED[kind] | OPTIONAL[kind]
    for adjunct in types(raw):
        allowed |= extension_members.get(adjunct, set())
    # Quantitative units may be specified on value annotations without a quantity
    # co-type only where their extension validator explicitly permits it.
    for member in raw.keys() - allowed:
        unknown = set(contexts) - EXTENSIONS - {"dtmi:dtdl:context;2", "dtmi:dtdl:context;3"}
        issue(
            "CONTEXTUALLY_INCOMPLETE"
            if unknown and not member.startswith("@")
            else "UNDEFINED_MEMBER",
            f"{member} is not defined on {kind} by known active types.",
            member,
        )
    if "name" in raw:
        name = raw["name"]
        if (
            not isinstance(name, str)
            or len(name) > 512
            or not re.fullmatch(r"[A-Za-z](?:[A-Za-z0-9_]*[A-Za-z0-9])?", name)
        ):
            issue(
                "PROGRAMMING_NAME", "Expected a programming name (maximum 512 characters).", "name"
            )
    if "comment" in raw and (not isinstance(raw["comment"], str) or len(raw["comment"]) > 512):
        issue("METADATA_LENGTH", "comment must be a string of at most 512 characters.", "comment")
    if "commandType" in raw and raw["commandType"] not in ("synchronous", "asynchronous"):
        issue("COMMAND_TYPE", "commandType must be synchronous or asynchronous.", "commandType")
    if kind == "MapKey" and raw.get("schema") != "string":
        issue("SCHEMA_SHAPE", "MapKey schema must be string.", "schema")
    if version2:
        for member in ("name", "displayName"):
            value = raw.get(member, "")
            texts = value.values() if isinstance(value, dict) else [value]
            if any(isinstance(v, str) and len(v) > 64 for v in texts):
                issue("DTDL_V2_LENGTH", f"DTDL v2 {member} is limited to 64 characters.", member)
        identifier = raw.get("@id", "")
        if identifier and (
            not isinstance(identifier, str)
            or ";" not in identifier
            or "." in identifier.partition(";")[2]
        ):
            issue("DTDL_V2_IDENTIFIER", "DTDL v2 requires a one-part DTMI version.", "@id")
        for member, minimum, maximum in (
            ("fields", 1, 30),
            ("enumValues", 1, 100),
            ("extends", 0, 2),
            ("properties", 0, 300),
        ):
            required = (
                kind == "Object" and member == "fields" or kind == "Enum" and member == "enumValues"
            )
            value = raw.get(member, [])
            if (
                required
                and member not in raw
                or (
                    isinstance(value, list)
                    and not minimum <= len(value) <= maximum
                    and (required or member in raw)
                )
            ):
                issue(
                    "DTDL_V2_COUNT",
                    f"DTDL v2 {member} requires {minimum}..{maximum} values.",
                    member,
                )
        quantities = types(raw) & QUANTITY_UNITS.keys()
        if len(quantities) > 1:
            issue("DTDL_V2_QUANTITY", "DTDL v2 permits one semantic quantity type.", "@type")
        if quantities and "unit" not in raw:
            issue("DTDL_V2_QUANTITY", "DTDL v2 quantity requires a unit.", "unit")
    return findings
