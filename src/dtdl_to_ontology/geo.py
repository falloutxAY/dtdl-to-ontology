"""Pinned DTDL v3 geospatial built-in source schemas.

The schema structures and identifiers were independently extracted from
DTDLParser 1.1.3. They describe DTDL source data only; no target mapping,
coordinate bounds, or target-specific representation is inferred here.
"""

GEO_SOURCE = (
    "https://github.com/Azure/opendigitaltwins-dtdl/blob/"
    "d19669a438a63be377c3cfc2fcabeac2e16ad55b/DTDL/v3/DTDL.v3.md"
)

_GEOMETRIES = {
    "point": "Point",
    "lineString": "LineString",
    "polygon": "Polygon",
    "multiPoint": "MultiPoint",
    "multiLineString": "MultiLineString",
    "multiPolygon": "MultiPolygon",
}


def _array(name: str, element_schema: dict) -> dict:
    return {
        "@id": f"dtmi:standard:schema:geospatial:{name};3",
        "@type": "Array",
        "elementSchema": element_schema,
    }


def _position() -> dict:
    return _array("position", "double")


def _linear_ring() -> dict:
    return _array("linearRingCoordinateArray", _position())


def _line_string() -> dict:
    return _array("lineStringCoordinateArray", _position())


def _polygon() -> dict:
    return _array("polygonCoordinateArray", _linear_ring())


def _coordinates(name: str) -> dict:
    if name == "point":
        return _position()
    if name == "lineString":
        return _array("lineStringCoordinateArray", _position())
    if name == "polygon":
        return _polygon()
    if name == "multiPoint":
        return _array("positionArray", _position())
    if name == "multiLineString":
        return _array("lineStringCoordinateArrayArray", _line_string())
    if name == "multiPolygon":
        return _array("polygonCoordinateArrayArray", _polygon())
    raise KeyError(name)


def _source_schema(name: str, geometry: str) -> dict:
    return {
        "@id": f"dtmi:standard:schema:geospatial:{name};3",
        "@type": "Object",
        "fields": [
            {
                "name": "type",
                "schema": {
                    "@id": f"dtmi:standard:schema:geospatial{geometry}Type;3",
                    "@type": "Enum",
                    "valueSchema": "string",
                    "enumValues": [{"name": name, "enumValue": geometry}],
                },
            },
            {"name": "coordinates", "schema": _coordinates(name)},
        ],
    }


# Keep these interpretation keys stable; source_schema is the exact expanded
# DTDL schema structure parsed from the pinned standard library.
GEOSCHEMAS = {
    name: {
        "@id": f"dtmi:standard:schema:geospatial:{name};3",
        "term": name,
        "geoJsonType": geometry,
        "source_schema": _source_schema(name, geometry),
    }
    for name, geometry in _GEOMETRIES.items()
}

GEO_ALIASES = {schema["@id"]: name for name, schema in GEOSCHEMAS.items()}
