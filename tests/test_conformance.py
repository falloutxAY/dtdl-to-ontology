"""Synthetic, independently reviewable DTDL source boundary regressions."""

import json

import pytest

from dtdl_to_ontology.cli import main
from dtdl_to_ontology.definition import build_parts
from dtdl_to_ontology.geo import GEOSCHEMAS
from dtdl_to_ontology.identifiers import automatic_id, valid_dtmi
from dtdl_to_ontology.loader import load
from dtdl_to_ontology.manifest import build_manifest
from dtdl_to_ontology.options import POLICIES, Options
from dtdl_to_ontology.plan import make_plan
from dtdl_to_ontology.resolver import resolve
from dtdl_to_ontology.source_limits import INTERFACE_BYTES
from dtdl_to_ontology.vocabulary import QUANTITATIVE

from .conftest import interface


def prop(schema="string", name="value", **fields):
    return {"@type": "Property", "name": name, "schema": schema, **fields}


@pytest.mark.parametrize(
    "value",
    [
        "dtmi:x",
        "dtmi:example:Sensor;1",
        "dtmi:example:Sensor;999999999.999999",
        "dtmi:a_b:A1;1.1",
    ],
)
def test_user_dtmi_positive(value):
    assert valid_dtmi(value, "interface")


@pytest.mark.parametrize(
    "value",
    [
        "dtmi:x;0",
        "dtmi:x;01",
        "dtmi:x;1.0",
        "dtmi:x;1.01",
        "dtmi:x;1000000000",
        "dtmi:x;1.1000000",
        "dtmi:_x;1",
        "dtmi:x_;1",
        "dtmi:a:_b;1",
        "dtmi:1x;1",
        "DTMI:x;1",
        "dtmi:x;1\n",
        "dtmi:dtdl:custom;1",
        "dtmi:standard:custom;1",
        ["dtmi:x;1"],
        1,
        None,
    ],
)
def test_user_dtmi_negative(value):
    assert not valid_dtmi(value, "interface")


@pytest.mark.parametrize("role,limit", [("interface", 128), ("element", 2048), ("generated", 4096)])
def test_dtmi_role_lengths(role, limit):
    assert valid_dtmi("dtmi:" + "a" * (limit - 5), role)
    assert not valid_dtmi("dtmi:" + "a" * (limit - 4), role)


def test_system_ids_never_accepted_as_user_identifiers():
    identifier = automatic_id("dtmi:example:Sensor;1.2", "contents", "reading")
    assert identifier == "dtmi:example:Sensor:_contents:__reading;1.2"
    assert valid_dtmi(identifier, "generated")
    assert not valid_dtmi(identifier, "element")


def test_versionless_scalar_reaches_deterministic_emission(write_models):
    raw = interface(contents=[prop()], **{"@id": "dtmi:example:Sensor"})
    resolution = resolve(load(write_models(raw)))
    assert not resolution.findings
    options = Options(roots=(raw["@id"],))
    plan = make_plan(resolution, options)
    assert not plan.blocked
    assert build_parts(plan, "Versionless") == build_parts(
        make_plan(resolution, options), "Versionless"
    )
    assert build_manifest(plan)["source_models"][raw["@id"]]["definition"] == raw


def test_v2_dependency_does_not_inherit_v3_per_interface_byte_limit(tmp_path):
    child = interface("Child", extends="dtmi:example:Base;1")
    base = interface("Base", **{"@context": "dtmi:dtdl:context;2"})
    padded_base = json.dumps(base)[:-1] + " " * INTERFACE_BYTES + "}"
    path = tmp_path / "mixed.json"
    path.write_text("[" + json.dumps(child) + "," + padded_base + "]", encoding="utf-8")
    result = resolve(load(path))
    assert not result.collection.findings
    assert not result.findings


def test_equivalent_normative_representations_and_originals(write_models):
    compact = interface(contents=[prop()], description={"en": "Example"})
    verbose = {
        "@context": "dtmi:dtdl:context;3",
        "@id": compact["@id"],
        "@type": ["dtmi:dtdl:class:Interface;3"],
        "dtmi:dtdl:property:contents;3": {
            "@type": ["dtmi:dtdl:class:Property;3"],
            "dtmi:dtdl:property:name;3": [{"@value": "value", "@type": "xsd:string"}],
            "dtmi:dtdl:property:schema;3": ["dtmi:dtdl:instance:Schema:string;3"],
        },
        "description": [{"@language": "en", "@value": "Example"}],
    }
    a = make_plan(resolve(load(write_models(compact))))
    b = make_plan(resolve(load(write_models(verbose))))
    assert not a.blocked and not b.blocked
    assert build_parts(a, "Same") == build_parts(b, "Same")
    manifest = build_manifest(b)
    assert manifest["source_models"][compact["@id"]]["definition"] == verbose
    assert manifest["normalization"]


@pytest.mark.parametrize(
    "context,content,member",
    [
        (
            "dtmi:dtdl:extension:annotation;1",
            prop(
                **{
                    "@type": ["Property", "dtmi:dtdl:extension:annotation:v2:ValueAnnotation"],
                    "annotates": "value",
                }
            ),
            "@type",
        ),
        (
            "dtmi:dtdl:extension:annotation;1",
            prop(
                **{
                    "@type": ["Property", "ValueAnnotation"],
                    "dtmi:dtdl:extension:annotation:v2:ValueAnnotation:annotates": "value",
                }
            ),
            "dtmi:dtdl:extension:annotation:v2:ValueAnnotation:annotates",
        ),
        (
            "dtmi:dtdl:extension:mqtt;1",
            {
                "@type": ["Telemetry", "Indexed"],
                "name": "reading",
                "schema": "double",
                "dtmi:dtdl:extension:mqtt:v2:Indexed:index": 0,
            },
            "dtmi:dtdl:extension:mqtt:v2:Indexed:index",
        ),
    ],
)
def test_extension_alias_version_is_checked_before_normalization(
    write_models, context, content, member
):
    collection = load(
        write_models(
            interface(contents=[content], **{"@context": ["dtmi:dtdl:context;3", context]})
        )
    )
    assert any(
        f.code == "EXTENSION_CONTEXT" and f.source.pointer == f"/0/contents/0/{member}"
        for f in collection.findings
    )
    assert make_plan(resolve(collection), Options(compatibility=True, policies=POLICIES)).blocked


@pytest.mark.parametrize(
    "change,code",
    [
        ({"name": ["a", "b"]}, "CARDINALITY"),
        ({"name": {"@value": "a", "@type": "xsd:integer"}}, "LITERAL"),
        ({"name": {"@value": "a", "extra": 1}}, "LITERAL"),
        ({"name": []}, "CARDINALITY"),
        ({"@id": ["dtmi:example:Property;1"]}, "IDENTIFIER"),
        ({"elementSchema": "string"}, "UNDEFINED_MEMBER"),
        ({"@reverse": {}}, "UNDEFINED_MEMBER"),
        ({"writable": "true"}, "CONTENT_SHAPE"),
    ],
)
def test_invalid_source_shapes_cannot_be_waived(write_models, change, code):
    raw = interface(contents=[prop(**change)])
    plan = make_plan(
        resolve(load(write_models(raw))), Options(compatibility=True, policies=POLICIES)
    )
    assert any(f.code == code and f.blocking for f in plan.findings)
    with pytest.raises(ValueError, match="blocking"):
        build_parts(plan, "Invalid")


@pytest.mark.parametrize(
    "value",
    [
        ["default", {"@language": "en", "@value": "duplicate"}],
        [{"@language": "en", "@value": "a"}, {"@language": "en", "@value": "b"}],
        [{"@language": "en-us", "@value": "a"}],
        [{"@language": "en", "@value": 1}],
        {"@language": "en", "@value": "a"},
        {"en": "a" * 513},
    ],
)
def test_invalid_localized_forms(write_models, value):
    collection = load(write_models(interface(description=value)))
    assert any(f.code == "LOCALIZED_STRING" for f in collection.findings)


def test_inline_parent_and_component_source_equivalence(write_models):
    parent = interface("Parent", [prop()])
    child = interface("Child", extends=parent)
    result = resolve(load(write_models(child)))
    assert not result.findings
    assert result.parents[child["@id"]] == [parent["@id"]]
    assert result.contents[child["@id"]]["value"].owner == parent["@id"]
    component = interface("Root", [{"@type": "Component", "name": "part", "schema": parent}])
    result = resolve(load(write_models(component)))
    assert not result.findings
    assert result.contents[component["@id"]]["part"].raw["schema"] == parent["@id"]


def test_registry_assigns_ids_without_changing_target_lineage(write_models):
    raw = interface(
        contents=[
            prop(
                {
                    "@type": "Object",
                    "fields": [
                        {"name": "x", "schema": "string"},
                    ],
                }
            )
        ]
    )
    result = resolve(load(write_models(raw)))
    assert not result.findings
    prefix = raw["@id"].replace(";1", ":_contents:__value")
    assert prefix + ";1" in result.graph.elements
    assert prefix + ":_schema;1" in result.graph.elements
    assert prefix + ":_schema:_fields:__x;1" in result.graph.elements
    plan = make_plan(result)
    assert set(plan.entities) == {raw["@id"]}


def test_explicit_id_duplicates_across_kinds(write_models):
    identifier = "dtmi:example:Duplicate;1"
    raw = interface(
        contents=[
            prop(**{"@id": identifier}),
            prop({"@id": identifier, "@type": "Object"}, name="other"),
        ]
    )
    result = resolve(load(write_models(raw)))
    assert any(f.code == "DUPLICATE_ID" for f in result.findings)


def test_same_partition_dependent_fields_and_content_are_resolved(write_models):
    raw = interface(
        contents=[
            prop(
                {
                    "@type": "Object",
                    "fields": [
                        {"@id": "dtmi:example:Field;1", "name": "x", "schema": "string"},
                    ],
                },
                name="first",
            ),
            prop({"@type": "Object", "fields": ["dtmi:example:Field;1"]}, name="second"),
        ]
    )
    result = resolve(load(write_models(raw)))
    assert not result.findings
    shape = result.contents[raw["@id"]]["second"].raw["schema"]
    assert shape["fields"][0]["name"] == "x"


@pytest.mark.parametrize(
    "kind", ["Field", "MapKey", "MapValue", "CommandRequest", "CommandResponse", "EnumValue"]
)
def test_nested_material_type_is_checked(write_models, kind):
    containers = {
        "Field": prop(
            {"@type": "Object", "fields": [{"@type": "Property", "name": "x", "schema": "string"}]}
        ),
        "MapKey": prop(
            {
                "@type": "Map",
                "mapKey": {"@type": "Property", "name": "key", "schema": "string"},
                "mapValue": {"name": "value", "schema": "string"},
            }
        ),
        "MapValue": prop(
            {
                "@type": "Map",
                "mapKey": {"name": "key", "schema": "string"},
                "mapValue": {"@type": "Property", "name": "value", "schema": "string"},
            }
        ),
        "CommandRequest": {
            "@type": "Command",
            "name": "go",
            "request": {"@type": "Property", "name": "request", "schema": "string"},
        },
        "CommandResponse": {
            "@type": "Command",
            "name": "go",
            "response": {"@type": "Property", "name": "response", "schema": "string"},
        },
        "EnumValue": prop(
            {
                "@type": "Enum",
                "valueSchema": "string",
                "enumValues": [{"@type": "Property", "name": "on", "enumValue": "on"}],
            }
        ),
    }
    result = resolve(load(write_models(interface(contents=[containers[kind]]))))
    assert any(f.code == "REFERENCE_TYPE" for f in result.findings)


@pytest.mark.parametrize("fields", [None, []])
def test_empty_object_is_valid_source_not_valid_target_struct(write_models, fields):
    schema = {"@type": "Object"}
    if fields is not None:
        schema["fields"] = fields
    result = resolve(load(write_models(interface(contents=[prop(schema)]))))
    assert not result.findings
    assert any(f.code == "EMPTY_STRUCT" for f in make_plan(result).findings)


@pytest.mark.parametrize("links,invalid", [(10, False), (11, True)])
def test_inheritance_depth_boundary(write_models, links, invalid):
    models = [
        interface(f"I{i}", extends=f"dtmi:example:I{i - 1};1") if i else interface("I0")
        for i in range(links + 1)
    ]
    result = resolve(load(write_models(*models)))
    assert any(f.code == "DTDL_EXTENDS_DEPTH" for f in result.findings) == invalid


@pytest.mark.parametrize("count,invalid", [(1024, False), (1025, True)])
def test_inheritance_union_count_boundary(write_models, count, invalid):
    parents = [interface(f"I{i}") for i in range(count)]
    root = interface(extends=[p["@id"] for p in parents])
    result = resolve(load(write_models(root, *parents)))
    assert any(f.code == "DTDL_EXTENDS_COUNT" for f in result.findings) == invalid


@pytest.mark.parametrize("links,invalid", [(5, False), (6, True)])
def test_schema_path_boundary(write_models, links, invalid):
    schema = {"@type": "Object"}
    for _ in range(links):
        schema = {"@type": "Object", "fields": [{"name": "x", "schema": schema}]}
    result = resolve(load(write_models(interface(contents=[prop(schema)]))))
    assert any(f.code == "DTDL_SCHEMA_DEPTH" for f in result.findings) == invalid


@pytest.mark.parametrize("extra,invalid", [(0, False), (1, True)])
def test_original_interface_utf8_byte_boundary(tmp_path, extra, invalid):
    text = json.dumps(interface(), ensure_ascii=False)
    text = text[:-1] + " " * (INTERFACE_BYTES + extra - len(text.encode("utf-8"))) + "}"
    path = tmp_path / "large.json"
    path.write_text(text, encoding="utf-8")
    result = resolve(load(path))
    assert any(f.code == "DTDL_INTERFACE_BYTES" for f in result.findings) == invalid


def test_many_interfaces_and_nested_interface_byte_accounting(tmp_path):
    parent = interface("Parent")
    text = json.dumps(parent)
    text = text[:-1] + " " * (INTERFACE_BYTES - len(text)) + "}"
    root = json.dumps(interface("Root", extends="INLINE")).replace('"INLINE"', text)
    path = tmp_path / "nested.json"
    path.write_text(root, encoding="utf-8")
    result = resolve(load(path))
    assert not result.findings
    assert (
        result.collection.interface_bytes[result.collection.models[parent["@id"]].source]
        == INTERFACE_BYTES
    )


def test_member_alias_conflict_is_nonwaivable_and_points_to_original(write_models):
    raw = interface(contents=[prop(**{"dtmi:dtdl:property:name;3": "other"})])
    collection = load(write_models(raw))
    finding = next(f for f in collection.findings if f.code == "MEMBER_ALIAS")
    assert finding.source.pointer == "/0/contents/0/dtmi:dtdl:property:name;3".replace("~", "~0")


@pytest.mark.parametrize("inline", [False, True])
@pytest.mark.parametrize("member", ["extends", "component"])
def test_v2_interface_dependency_keeps_its_own_context(write_models, inline, member):
    base = interface("Base", [prop()], **{"@context": "dtmi:dtdl:context;2"})
    target = base if inline else base["@id"]
    root = (
        interface(extends=target)
        if member == "extends"
        else interface(contents=[{"@type": "Component", "name": "part", "schema": target}])
    )
    result = resolve(load(write_models(*([root] if inline else [root, base]))))
    assert not result.collection.findings
    assert not result.findings
    assert result.collection.contexts_at(result.collection.models[base["@id"]].source) == (
        "dtmi:dtdl:context;2",
    )


@pytest.mark.parametrize(
    "schema,code",
    [
        ({"@type": "Object"}, "DTDL_V2_COUNT"),
        ({"@type": "Enum", "valueSchema": "string"}, "DTDL_V2_COUNT"),
        ({"@type": "Array", "elementSchema": "string"}, "DTDL_V2_PROPERTY_ARRAY"),
    ],
)
def test_v2_dependencies_are_not_relabelled_as_v3(write_models, schema, code):
    base = interface("Base", [prop(schema)], **{"@context": "dtmi:dtdl:context;2"})
    root = interface(extends=base["@id"])
    result = resolve(load(write_models(root, base)))
    assert any(f.code == code for f in result.findings)


def test_nested_contexts_apply_lowest_latest_version_without_inheriting_mqtt_metadata(write_models):
    base = interface(
        "Base",
        [prop()],
        **{
            "@context": ["dtmi:dtdl:context;3", "dtmi:dtdl:extension:mqtt;1"],
            "@type": ["Interface", "Mqtt"],
            "payloadFormat": "Json",
        },
    )
    root = interface(
        extends=base["@id"],
        contents=[
            {
                "@context": [
                    "dtmi:dtdl:extension:historization;1",
                    "dtmi:dtdl:extension:historization;2",
                    "dtmi:dtdl:extension:historization;1",
                ],
                "@type": ["Property", "Historized"],
                "name": "history",
                "schema": "double",
            }
        ],
    )
    result = resolve(load(write_models(root, base)))
    assert not result.findings
    field = result.contents[root["@id"]]["history"]
    contexts = result.collection.contexts_at(field.source)
    assert "dtmi:dtdl:extension:historization;1" in contexts
    assert "dtmi:dtdl:extension:historization;2" not in contexts
    assert "payloadFormat" not in result.collection.models[root["@id"]].raw


@pytest.mark.parametrize("geometry", sorted(GEOSCHEMAS))
@pytest.mark.parametrize("canonical", [False, True])
def test_each_geospatial_schema_is_valid_source_but_has_no_new_target_fallback(
    write_models, geometry, canonical
):
    schema = GEOSCHEMAS[geometry]["@id"] if canonical else geometry
    root = interface(contents=[prop(schema)])
    result = resolve(load(write_models(root)))
    assert not result.findings
    plan = make_plan(result, Options(compatibility=True, policies=POLICIES))
    assert any(f.code == "GEOSPATIAL_MAPPING" and f.blocking for f in plan.findings)
    manifest = build_manifest(plan)
    value = next(e for e in manifest["source_elements"].values() if e["types"] == "Property")
    assert value["semantics"]["geospatial"]["term"] == geometry
    assert not value["semantics"]["target_enforcement"]


@pytest.mark.parametrize(
    "context,kind,code",
    [
        ("historization;1", "Property", "HISTORIZATION_BINDING"),
        ("historization;2", "Telemetry", "HISTORIZATION_BINDING"),
        ("mqtt;1", "Interface", "MQTT_RUNTIME"),
        ("mqtt;2", "Interface", "MQTT_RUNTIME"),
        ("mqtt;3", "Interface", "MQTT_RUNTIME"),
        ("requirement;1", "Field", "FIELD_PRESENCE"),
    ],
)
def test_new_source_semantics_have_explicit_cli_blockers_not_workarounds(
    write_models, tmp_path, capsys, context, kind, code
):
    ctx = ["dtmi:dtdl:context;3", "dtmi:dtdl:extension:" + context]
    root = interface(**{"@context": ctx})
    if kind == "Interface":
        root.update({"@type": ["Interface", "Mqtt"], "payloadFormat": "Json"})
    elif kind == "Field":
        root["contents"] = [
            prop(
                {
                    "@type": "Object",
                    "fields": [
                        {"@type": ["Field", "Required"], "name": "x", "schema": "double"},
                        {"name": "y", "schema": "double"},
                    ],
                }
            )
        ]
    else:
        root["contents"] = [
            {
                "@type": [kind, "Historized"],
                "name": "reading",
                "schema": "double",
            }
        ]
    path = write_models(root)
    output = tmp_path / "result"
    args = ["convert", str(path), "--name", "Blocked", "--output", str(output), "--compatibility"]
    for policy in sorted(POLICIES):
        args += ["--policy", policy]
    assert main(args) == 1
    capsys.readouterr()
    report = json.loads((output / "report.json").read_text())
    assert any(f["code"] == code and f["blocking"] for f in report["findings"])
    assert not (output / "definition.json").exists()
    manifest = json.loads((output / "manifest.json").read_text())
    if kind == "Field":
        fields = [e for e in manifest["source_elements"].values() if "presence" in e["semantics"]]
        assert sorted(e["semantics"]["presence"]["required"] for e in fields) == [False, True]


def test_unknown_extension_is_indeterminate_not_proven_invalid(write_models):
    root = interface(
        contents=[prop(extra="value")],
        **{
            "@context": ["dtmi:dtdl:context;3", "dtmi:example:custom;1"],
        },
    )
    result = resolve(load(write_models(root)))
    assert any(
        f.code == "UNKNOWN_EXTENSION" and "indeterminate" in f.message for f in result.findings
    )
    assert any(f.code == "CONTEXTUALLY_INCOMPLETE" for f in result.findings)
    assert not any(f.code == "UNDEFINED_MEMBER" for f in result.findings)


def test_named_schema_partition_remains_private_through_inheritance(write_models):
    base = interface(
        "Base",
        schemas=[
            {
                "@id": "dtmi:example:Private;1",
                "@type": "Object",
            }
        ],
    )
    root = interface(extends=base["@id"], contents=[prop("dtmi:example:Private;1")])
    result = resolve(load(write_models(root, base)))
    assert any(f.code == "PARTITION_REFERENCE" and f.dtmi == root["@id"] for f in result.findings)


def test_aliases_do_not_enable_wrong_core_or_extension_versions(write_models):
    root = interface(
        contents=[
            {
                "@type": "dtmi:dtdl:class:Property;2",
                "name": "reading",
                "schema": "dtmi:dtdl:instance:Schema:string;2",
            }
        ]
    )
    result = resolve(load(write_models(root)))
    assert any(f.code == "TERM_VERSION" for f in result.collection.findings)
    root["contents"][0] = {
        "@type": ["Property", "dtmi:dtdl:extension:quantitativeTypes:class:Temperature;2"],
        "name": "reading",
        "schema": "double",
    }
    root["@context"] = ["dtmi:dtdl:context;3", QUANTITATIVE]
    assert any(f.code == "UNKNOWN_TYPE" for f in resolve(load(write_models(root))).findings)


@pytest.mark.parametrize("total,invalid", [(100_000, False), (100_001, True)])
def test_contents_value_count_boundary_is_distinct_from_byte_limit(write_models, total, invalid):
    # These are size-stress models, not globally conformant models: their original
    # Interface text also exceeds 1 MiB. The count boundary is tested independently.
    values = [{"name": f"v{i}", "enumValue": i} for i in range(total - 2)]
    raw = interface(
        contents=[prop({"@type": "Enum", "valueSchema": "integer", "enumValues": values})]
    )
    result = resolve(load(write_models(raw)))
    assert any(f.code == "DTDL_CONTENT_COUNT" for f in result.findings) == invalid
    assert any(f.code == "DTDL_INTERFACE_BYTES" for f in result.findings)
