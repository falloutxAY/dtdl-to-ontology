import uuid

import pytest

from dtdl_to_ontology.naming import doc_comments, lineage, property_name, quote, target_name


def test_readable_names_and_uuid_are_order_independent():
    identities = [
        "dtmi:example:Sensor;1",
        "dtmi:example:sensor;1",
        "dtmi:example:Sensor;2",
        "dtmi:a_b:Sensor;1",
        "dtmi:a:b:Sensor;1",
        "dtmi:example:Sensor;1/edge#source",
    ]
    forward = {identity: target_name(identity) for identity in identities}
    backward = {identity: target_name(identity) for identity in reversed(identities)}
    assert forward == backward
    assert forward["dtmi:example:Sensor;1"].qualified == "example#Sensor"
    assert forward["dtmi:example:Sensor;1"].name == forward["dtmi:example:Sensor;2"].name
    assert (
        forward["dtmi:example:Sensor;1"].lineage_tag != forward["dtmi:example:Sensor;2"].lineage_tag
    )
    assert all(uuid.UUID(name.lineage_tag).version == 5 for name in forward.values())
    assert lineage("same", "source") != lineage("same", "target")
    assert property_name("owner", "height") == "height"


def test_willow_names_are_readable_without_model_version_or_hashes():
    name = target_name("dtmi:com:willowinc:Settings;1")
    assert name.namespace == "com_willowinc"
    assert name.name == "Settings"
    assert name.lineage_tag == "41502e52-c2be-58eb-a536-b65f352b74e8"
    assert (
        target_name("dtmi:com:willowinc:Building;1/ownedBy", "relationship").name
        == "Building_ownedBy"
    )


def test_control_like_text_cannot_inject_a_declaration():
    assert quote("namespace#O'Brien") == "'namespace#O''Brien'"
    assert doc_comments("safe\r\nentity 'injected'\n\tproperty x", "\t") == [
        "\t/// safe",
        "\t/// entity 'injected'",
        "\t/// \tproperty x",
    ]
    with pytest.raises(ValueError, match="control"):
        quote("x\nentity y")
    name = property_name("owner", "x\nproperty 'injected'")
    assert "\n" not in quote(name)
