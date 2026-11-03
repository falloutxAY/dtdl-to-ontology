"""Normative source limits, separate from input safety guards and Fabric limits."""

import json

from .model import Collection, Finding, Source
from .normalization import term
from .source_graph import Element, SourceGraph, types

INTERFACE_BYTES = 1024 * 1024
CONTENT_MEMBERS = {
    "contents",
    "fields",
    "enumValues",
    "request",
    "response",
    "properties",
    "schema",
    "elementSchema",
    "mapValue",
}


def object_sizes(data: bytes, document: object, source: Source) -> dict[Source, int]:
    """Measure original UTF-8 object text, including whitespace within braces."""
    text = data.decode("utf-8-sig")
    decoder = json.JSONDecoder()
    sizes: dict[Source, int] = {}

    def whitespace(pos: int) -> int:
        while pos < len(text) and text[pos] in " \r\n\t":
            pos += 1
        return pos

    def scan(value: object, pos: int, location: Source) -> int:
        pos = whitespace(pos)
        start = pos
        if isinstance(value, dict):
            pos = whitespace(pos + 1)
            for key, child in value.items():
                _, pos = decoder.raw_decode(text, pos)
                pos = whitespace(pos)
                pos = scan(child, pos + 1, location.child(key))
                pos = whitespace(pos)
                if text[pos] == ",":
                    pos = whitespace(pos + 1)
            pos += 1
            sizes[location] = len(text[start:pos].encode("utf-8"))
            return pos
        if isinstance(value, list):
            pos = whitespace(pos + 1)
            for index, child in enumerate(value):
                pos = whitespace(scan(child, pos, location.child(index)))
                if text[pos] == ",":
                    pos = whitespace(pos + 1)
            return pos + 1
        _, end = decoder.raw_decode(text, pos)
        return end

    scan(document, 0, source)
    return sizes


def interface_size(raw: dict, source: Source, sizes: dict[Source, int]) -> int:
    def nested(value: object, location: Source) -> int:
        if isinstance(value, dict):
            raw_types = value.get("@type", [])
            raw_types = [raw_types] if isinstance(raw_types, str) else raw_types
            if isinstance(raw_types, list) and any(
                isinstance(item, str) and term(item) == "Interface" for item in raw_types
            ):
                return sizes.get(location, 0)
            return sum(nested(child, location.child(key)) for key, child in value.items())
        if isinstance(value, list):
            return sum(nested(child, location.child(i)) for i, child in enumerate(value))
        return 0

    return sizes.get(source, 0) - sum(
        nested(child, source.child(key)) for key, child in raw.items()
    )


def validate_limits(graph: SourceGraph, collection: Collection) -> list[Finding]:
    findings: list[Finding] = []

    def issue(code: str, message: str, element: Element) -> None:
        findings.append(Finding(code, message, element.source, element.owner))

    def reachable(root: Element, members: set[str]) -> dict[str, Element]:
        seen: dict[str, Element] = {}
        pending = [root]
        while pending:
            element = pending.pop()
            if element.identity in seen:
                continue
            seen[element.identity] = element
            pending.extend(
                child
                for member, child in element.edges
                if member in members
                or (
                    "contents" in members
                    and "Interface" in types(element.raw)
                    and member == "extends"
                )
            )
        return seen

    def values(element: Element, members: set[str]) -> int:
        return sum(
            len(value) if isinstance(value, list) else 1
            for member, value in element.raw.items()
            if member in members
        )

    def longest(root: Element, members: set[str], weighted: set[str], limit: int) -> int:
        memo: dict[str, int] = {}
        active: set[str] = set()

        def visit(element: Element, depth: int) -> int:
            if element.identity in active or depth >= 128:
                return limit + 1
            if element.identity in memo:
                return memo[element.identity]
            active.add(element.identity)
            length = max(
                (
                    (member in weighted) + visit(child, depth + 1)
                    for member, child in element.edges
                    if member in members
                ),
                default=0,
            )
            active.remove(element.identity)
            memo[element.identity] = length
            return length

        return visit(root, 0)

    for element in graph.elements.values():
        kinds = types(element.raw)
        version2 = graph.version(element) == 2
        if "Interface" in kinds:
            if not version2 and collection.interface_bytes.get(element.source, 0) > INTERFACE_BYTES:
                issue(
                    "DTDL_INTERFACE_BYTES",
                    "Interface text exceeds 1 MiB, excluding nested Interfaces.",
                    element,
                )
            ancestors = reachable(element, {"extends"})
            if not version2 and sum(values(e, {"extends"}) for e in ancestors.values()) > 1024:
                issue(
                    "DTDL_EXTENDS_COUNT",
                    "Inheritance hierarchy exceeds 1024 extends values.",
                    element,
                )
            if longest(element, {"extends"}, {"extends"}, 10) > 10:
                issue("DTDL_EXTENDS_DEPTH", "Inheritance path exceeds 10 extends members.", element)
            content: dict[str, Element] = {}
            for ancestor in ancestors.values():
                content.update(reachable(ancestor, CONTENT_MEMBERS))
            if not version2 and sum(values(e, CONTENT_MEMBERS) for e in content.values()) > 100_000:
                issue("DTDL_CONTENT_COUNT", "Contents hierarchy exceeds 100000 values.", element)
            if version2 and sum(values(e, {"contents"}) for e in ancestors.values()) > 300:
                issue("DTDL_V2_COUNT", "DTDL v2 Interface exceeds 300 inherited contents.", element)
        if kinds & {"Array", "Map", "Object"}:
            if longest(element, CONTENT_MEMBERS - {"contents"}, {"schema", "elementSchema"}, 5) > 5:
                issue(
                    "DTDL_SCHEMA_DEPTH",
                    "Complex-schema path exceeds five schema/elementSchema members.",
                    element,
                )
        if "Component" in kinds:
            descendants = reachable(element, {"schema", "contents"})
            if any(
                "Component" in types(child.raw) and child is not element
                for child in descendants.values()
            ):
                issue(
                    "DTDL_NESTED_COMPONENT",
                    "A Component cannot contain another Component through schema/contents.",
                    element,
                )
        if version2 and "Property" in kinds:
            descendants = reachable(element, CONTENT_MEMBERS)
            if any("Array" in types(child.raw) for child in descendants.values()) or any(
                child.raw.get("schema")
                in {
                    "point",
                    "lineString",
                    "polygon",
                    "multiPoint",
                    "multiLineString",
                    "multiPolygon",
                }
                if isinstance(child.raw.get("schema"), str)
                else False
                for child in descendants.values()
            ):
                issue(
                    "DTDL_V2_PROPERTY_ARRAY",
                    "DTDL v2 Property cannot contain Array/geospatial schemas.",
                    element,
                )
    return findings
