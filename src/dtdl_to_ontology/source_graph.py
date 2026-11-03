"""Partition-scoped source elements, independent of target naming and lineage."""

import re
from dataclasses import dataclass, field

from .identifiers import automatic_id, valid_dtmi
from .model import Collection, Finding, Source
from .normalization import ELEMENT_MEMBERS, MATERIALS, PRIMITIVES, SETS

SCHEMAS = {"Array", "Enum", "Map", "Object"}
CONTENTS = {"Property", "Telemetry", "Command", "Component", "Relationship"}


def types(raw: dict) -> set[str]:
    value = raw.get("@type", [])
    return (
        {value}
        if isinstance(value, str)
        else {v for v in value if isinstance(v, str)}
        if isinstance(value, list)
        else set()
    )


@dataclass
class Element:
    identity: str
    owner: str
    raw: dict
    source: Source
    explicit: bool
    edges: list[tuple[str, "Element"]] = field(default_factory=list)


class SourceGraph:
    def __init__(self, collection: Collection):
        self.collection = collection
        self.elements: dict[str, Element] = {}
        self.by_object: dict[int, Element] = {}
        self.findings: list[Finding] = []

    def issue(self, code: str, message: str, owner: str, source: Source) -> None:
        self.findings.append(Finding(code, message, source, owner))

    def index(
        self, raw: dict, owner: str, source: Source, parent: str = "", member: str = ""
    ) -> Element | None:
        if id(raw) in self.by_object:
            return self.by_object[id(raw)]
        source = self.collection.location(raw, source)
        material = types(raw) & MATERIALS
        is_interface = "Interface" in material
        identifier = raw.get("@id")
        explicit = "@id" in raw
        if explicit and not valid_dtmi(identifier, "interface" if is_interface else "element"):
            self.issue("IDENTIFIER", "Invalid explicit user DTMI.", owner, source.child("@id"))
            return None
        if not explicit:
            name = raw.get("name") if member in SETS else None
            if member in {"extends", "schemas"} or not parent:
                self.issue(
                    "IDENTIFIER",
                    f"{member or 'Interface'} requires an explicit @id.",
                    owner,
                    source,
                )
                return None
            if member in SETS and not isinstance(name, str):
                return None
            if isinstance(name, str) and not re.fullmatch(
                r"[A-Za-z](?:[A-Za-z0-9_]*[A-Za-z0-9])?", name
            ):
                self.issue(
                    "PROGRAMMING_NAME",
                    "Invalid programming name.",
                    owner,
                    self.collection.location(raw, source, "name"),
                )
                return None
            identifier = automatic_id(parent, member, name)
            if not valid_dtmi(identifier, "generated"):
                self.issue("IDENTIFIER", "Generated DTMI exceeds system bounds.", owner, source)
                return None
        if is_interface:
            owner = identifier
        element = Element(identifier, owner, raw, source, explicit)
        self.by_object[id(raw)] = element
        previous = self.elements.get(identifier)
        if previous:
            self.issue(
                "DUPLICATE_ID",
                f"Element DTMI already declared at {previous.source}.",
                owner,
                source,
            )
        else:
            self.elements[identifier] = element
        for key in ELEMENT_MEMBERS:
            value = raw.get(key)
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, dict):
                    self.index(child, owner, source.child(key), identifier, key)
        return element

    def lookup(
        self,
        value: str,
        owner: str,
        source: Source,
        expected: set[str],
        code: str = "MISSING_DEPENDENCY",
    ) -> Element | None:
        if not valid_dtmi(value):
            self.issue("IDENTIFIER", "Invalid dependent-reference DTMI.", owner, source)
            return None
        element = self.elements.get(value)
        if element is None:
            self.issue(code, f"Unresolved dependent reference: {value}", owner, source)
        elif element.owner != owner and "Interface" not in types(element.raw):
            self.issue(
                "PARTITION_REFERENCE", f"Private element belongs to {element.owner}.", owner, source
            )
        elif not types(element.raw) & expected:
            self.issue(
                "REFERENCE_TYPE", f"Reference requires {'/'.join(sorted(expected))}.", owner, source
            )
        else:
            return element
        return None

    def expected(self, raw: dict, member: str) -> set[str]:
        return {
            "extends": {"Interface"},
            "schemas": SCHEMAS,
            "contents": CONTENTS,
            "fields": {"Field"},
            "enumValues": {"EnumValue"},
            "mapKey": {"MapKey"},
            "mapValue": {"MapValue"},
            "request": {"CommandRequest"},
            "response": {"CommandResponse"},
            "properties": {"Property"},
        }.get(member, {"Interface"} if "Component" in types(raw) else SCHEMAS)

    def version(self, element: Element) -> int:
        contexts = self.collection.active_contexts.get(element.source, ())
        return 2 if "dtmi:dtdl:context;2" in contexts else 3

    def connect(self) -> None:
        # All elements, including excluded roots and omitted runtime contents,
        # are validated before any projection policy can run.
        for element in list(self.elements.values()):
            for member in ELEMENT_MEMBERS & element.raw.keys():
                value = element.raw[member]
                values = value if isinstance(value, list) else [value]
                for index, child in enumerate(values):
                    source = self.collection.location(element.raw, element.source, member)
                    if isinstance(value, list):
                        source = source.child(index)
                    expected = self.expected(element.raw, member)
                    target = None
                    if isinstance(child, dict):
                        target = self.by_object.get(id(child))
                        if target and not types(child) & expected:
                            self.issue(
                                "REFERENCE_TYPE",
                                f"Invalid {member} material type.",
                                element.owner,
                                target.source,
                            )
                            target = None
                    elif isinstance(child, str):
                        # Standard schemas are terminal vocabulary, not user dependencies.
                        if (
                            expected == SCHEMAS
                            and member != "schemas"
                            and (
                                child in PRIMITIVES
                                or not child.startswith("dtmi:")
                                or child.startswith("dtmi:standard:schema:geospatial:")
                            )
                        ):
                            continue
                        code = {"extends": "MISSING_PARENT", "schema": "MISSING_SCHEMA"}.get(
                            member, "MISSING_DEPENDENCY"
                        )
                        if "Component" in types(element.raw):
                            code = "MISSING_COMPONENT"
                        target = self.lookup(child, element.owner, source, expected, code)
                    else:
                        self.issue(
                            "ELEMENT_SHAPE",
                            f"{member} requires an element or reference.",
                            element.owner,
                            source,
                        )
                    if target:
                        if self.version(target) != self.version(element) and (
                            self.version(element) == 2
                            or member
                            not in {
                                "schema",
                                "elementSchema",
                                "extends",
                                "contents",
                                "properties",
                            }
                        ):
                            self.issue(
                                "DEPENDENCY_VERSION",
                                f"{member} cannot include that DTDL version.",
                                element.owner,
                                source,
                            )
                        element.edges.append((member, target))

    def cycles(self) -> None:
        visited: set[str] = set()
        active: set[str] = set()

        def visit(element: Element, depth: int) -> None:
            if element.identity in active:
                self.issue(
                    "DEPENDENCY_CYCLE",
                    "Dependent-reference path returns to itself.",
                    element.owner,
                    element.source,
                )
                return
            if element.identity in visited:
                return
            if depth >= 128:
                self.issue(
                    "RESOLUTION_LIMIT",
                    "Dependency traversal exceeds 128 levels.",
                    element.owner,
                    element.source,
                )
                return
            active.add(element.identity)
            for _, child in element.edges:
                visit(child, depth + 1)
            active.remove(element.identity)
            visited.add(element.identity)

        for element in self.elements.values():
            visit(element, 0)

    def build(self) -> "SourceGraph":
        for model in self.collection.models.values():
            self.index(model.raw, model.id, model.source)
        self.connect()
        self.cycles()
        return self

    def expand(self, raw: dict) -> dict:
        """Expand non-schema dependent forms; keep schema references as identities."""
        for member in ELEMENT_MEMBERS & raw.keys():
            value = raw[member]
            values = value if isinstance(value, list) else [value]
            expanded = []
            for child in values:
                if isinstance(child, dict) and "Interface" in types(child):
                    child = child.get("@id", child)
                elif isinstance(child, str) and member not in {
                    "schema",
                    "elementSchema",
                    "extends",
                    "schemas",
                }:
                    element = self.by_object.get(id(raw))
                    target = self.elements.get(child)
                    if element and target and element.owner == target.owner:
                        child = target.raw
                expanded.append(child)
            raw[member] = expanded if isinstance(value, list) else expanded[0]
        return raw
