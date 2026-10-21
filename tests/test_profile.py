from dataclasses import replace

from dtdl_to_ontology.profile import DEFAULT_PROFILE


def test_unverified_relationships_cannot_be_enabled_by_flag_alone():
    assert not DEFAULT_PROFILE.relationships_enabled
    assert not replace(DEFAULT_PROFILE, unbound_relationships=True).relationships_enabled
    assert not DEFAULT_PROFILE.inheritance


def test_feature_declaration_does_not_claim_service_acceptance():
    declared = replace(DEFAULT_PROFILE, inheritance=True)
    assert declared.to_dict()["service_acceptance"] == "unverified"
