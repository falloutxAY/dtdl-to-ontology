import pytest

from dtdl_to_ontology.semantic import compare_semantics, parse_tmdl


def parts(*, data_type="string", description="A label.", relation=True):
    result = {
        "namespaces/ns.tmdl": "namespace 'n'\n\tlineageTag: ns-lineage\n",
        "entities/a.tmdl": (
            f"/// {description}\n"
            "entity 'n#A'\n"
            "\tlineageTag: entity-lineage\n"
            "\n"
            "/// Label description.\n"
            "property 'label'\n"
            "\tlineageTag: property-lineage\n"
            f"\tdataType: {data_type}\n"
            "\tannotation 'source' = \"dtdl\"\n"
        ),
    }
    if relation:
        result["entityRelationships.tmdl"] = (
            "entityRelationship 'n#A_has_B'\n"
            "\tlineageTag: relation-lineage\n"
            "\tfromEntity: 'n#A'\n"
            "\ttoEntity: 'n#B'\n"
        )
    return result


def test_semantic_comparison_ignores_part_order_and_reports_mapping_context():
    manifest = {
        "policies": ["flatten-inheritance", "json-objects"],
        "transformations_and_findings": [
            {
                "code": "UNBOUND_STRUCT",
                "approved": True,
                "selected": True,
                "policy": "json-objects",
                "dtmi": "dtmi:example:A;1",
                "source": {"file": "a.json", "pointer": "/contents/0"},
            }
        ],
    }

    result = compare_semantics(
        parts(),
        dict(reversed(list(parts().items()))),
        manifest=manifest,
    )

    assert result["status"] == "completed"
    assert result["supported_fields_match"]
    assert result["differences"]["entities"]["changed"] == {}
    assert result["mapping_loss_context"] == {
        "selected_policies": ["flatten-inheritance", "json-objects"],
        "intentional_mapping_losses": [
            {
                "code": "UNBOUND_STRUCT",
                "policy": "json-objects",
                "count": 1,
                "source_examples": [
                    {
                        "dtmi": "dtmi:example:A;1",
                        "source": {"file": "a.json", "pointer": "/contents/0"},
                    }
                ],
            }
        ],
    }
    assert "not full semantic equivalence" in result["scope"]


def test_semantic_comparison_reports_entities_properties_and_relationships():
    submitted = parts()
    returned = parts(data_type="double", description="Changed description.", relation=False)
    returned["entities/extra.tmdl"] = "entity 'n#Extra'\n\tlineageTag: extra-lineage\n"

    result = compare_semantics(submitted, returned)

    assert not result["supported_fields_match"]
    assert result["differences"]["entities"]["additional"] == ["n#Extra"]
    assert result["differences"]["entities"]["changed"]["n#A"]["description"] == {
        "submitted": "A label.",
        "returned": "Changed description.",
    }
    assert result["differences"]["properties"]["n#A"]["changed"]["label"]["dataType"] == {
        "submitted": "string",
        "returned": "double",
    }
    assert result["differences"]["relationships"]["missing"] == ["n#A_has_B"]


def test_parser_rejects_duplicate_semantic_identifiers():
    with pytest.raises(ValueError, match="Duplicate TMDL"):
        parse_tmdl(
            {"one.tmdl": ("entity 'n#A'\n\tlineageTag: one\nentity 'n#A'\n\tlineageTag: two\n")}
        )


def test_parser_rejects_malformed_complex_type_json():
    with pytest.raises(ValueError, match="Malformed complexDataType JSON"):
        parse_tmdl(
            {
                "one.tmdl": (
                    "entity 'n#A'\n\tlineageTag: one\n"
                    "\nproperty 'value'\n\tcomplexDataType = {invalid}\n"
                )
            }
        )


def test_parser_rejects_unrecognized_semantic_fields():
    with pytest.raises(ValueError, match="Unsupported TMDL construct"):
        parse_tmdl({"one.tmdl": "entity 'n#A'\n\tisHidden: true\n"})


@pytest.mark.parametrize("indent", ["\t", "    "])
def test_entity_annotations_after_properties_keep_their_own_scope(indent):
    submitted = {
        "entity.tmdl": (
            "entity 'example#Settings'\n"
            f"{indent}annotation dtdlModelId = dtmi:example:Settings;1\n"
            f"{indent}property enabled\n"
            f"{indent}{indent}dataType: boolean\n"
            f"{indent}{indent}annotation dtdlModelId = dtmi:example:Base;2\n"
        )
    }
    returned = {
        "entity.tmdl": (
            "entity 'example#Settings'\n"
            f"{indent}property enabled\n"
            f"{indent}{indent}dataType: boolean\n"
            f"{indent}{indent}annotation dtdlModelId = dtmi:example:Base;2\n"
            f"{indent}annotation dtdlModelId = dtmi:example:Settings;1\n"
        )
    }
    assert compare_semantics(submitted, returned)["supported_fields_match"]
    record = parse_tmdl(returned)["entities"]["example#Settings"]
    assert record["annotations"]["dtdlModelId"] == "dtmi:example:Settings;1"
    assert record["properties"]["enabled"]["annotations"]["dtdlModelId"] == "dtmi:example:Base;2"


def test_duplicate_annotations_within_the_same_scope_still_fail():
    with pytest.raises(ValueError, match="Duplicate annotation"):
        parse_tmdl(
            {"one.tmdl": ('entity A\n\tannotation source = "a"\n\tannotation source = "b"\n')}
        )


def test_relationship_labels_are_compared():
    source = {
        "relations.tmdl": (
            "entityRelationship Building_ownedBy\n"
            "\tfromEntity: Building\n\ttoEntity: Agent\n\tlabel: ownedBy\n"
        )
    }
    changed = {
        "relations.tmdl": source["relations.tmdl"].replace(
            "\tlabel: ownedBy\n", "\tlabel: operatedBy\n"
        )
    }
    comparison = compare_semantics(source, changed)
    assert not comparison["supported_fields_match"]
    assert "label" in comparison["differences"]["relationships"]["changed"]["Building_ownedBy"]


def test_label_string_quotes_are_not_identifier_quoting():
    source = {"relations.tmdl": "entityRelationship R\n\tlabel: ownedBy\n"}
    quoted = {"relations.tmdl": "entityRelationship R\n\tlabel: 'ownedBy'\n"}
    assert not compare_semantics(source, quoted)["supported_fields_match"]


def test_annotation_values_are_text_not_json_literals():
    parts = {
        "one.tmdl": ('entity Settings\n\tannotation version = 1\n\tannotation value = "quoted"\n')
    }
    annotations = parse_tmdl(parts)["entities"]["Settings"]["annotations"]
    assert annotations == {"version": "1", "value": '"quoted"'}
