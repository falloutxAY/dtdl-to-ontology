import uuid

import pytest

from dtdl_to_ontology.naming import doc_comments, lineage, property_name, quote, target_name


def test_names_and_uuid_are_order_independent_versioned_and_collision_safe():
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
    assert len({name.qualified.casefold() for name in forward.values()}) == len(identities)
    assert all(uuid.UUID(name.lineage_tag).version == 5 for name in forward.values())
    assert lineage("same", "source") != lineage("same", "target")
    assert property_name("owner", "X").casefold() != property_name("owner", "x").casefold()


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
