import json

import pytest

from dtdl_to_ontology.model import Source
from dtdl_to_ontology.options import Options, load_options


def array_loss(options):
    return options.loss(
        "COLLECTION",
        "Array",
        Source("A.json", "/contents/0"),
        "dtmi:example:A;1",
        "json-collections",
        "Approve JSON strings.",
        "No native typed collection.",
    )


def test_compatibility_mode_does_not_approve_all_losses():
    assert array_loss(Options()).blocking
    assert array_loss(Options(compatibility=True)).blocking
    approved = Options(compatibility=True, policies=frozenset({"json-collections"}))
    assert not array_loss(approved).blocking
    assert array_loss(approved).approved


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"policies": frozenset({"unknown"})}, "Unknown policies"),
        ({"policies": frozenset({"json-collections"})}, "require --compatibility"),
        (
            {"compatibility": True, "omissions": frozenset({"dtmi:example:A;1/r"})},
            "omit-relationships policy",
        ),
        (
            {
                "compatibility": True,
                "policies": frozenset({"omit-relationships"}),
                "omissions": frozenset({"*"}),
            },
            "exact DTMI",
        ),
    ],
)
def test_invalid_policy_requests_fail(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Options(**kwargs)


def test_unknown_config_field_cannot_enable_unverified_relationships(tmp_path):
    config = tmp_path / "options.json"
    config.write_text(json.dumps({"unbound_relationships": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown mapping"):
        load_options(config)
