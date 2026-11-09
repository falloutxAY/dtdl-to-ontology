from dataclasses import replace

from dtdl_to_ontology.profile import DEFAULT_PROFILE, TargetProfile


def test_unverified_relationships_cannot_be_enabled_by_flag_alone():
    assert not TargetProfile().relationships_enabled
    assert not replace(TargetProfile(), unbound_relationships=True).relationships_enabled
    assert not DEFAULT_PROFILE.inheritance


def test_default_relationship_profile_has_recorded_acceptance():
    assert DEFAULT_PROFILE.relationships_enabled
    assert DEFAULT_PROFILE.relationship_evidence.endswith("#verified-definition-shapes")
    assert DEFAULT_PROFILE.to_dict()["service_acceptance"] == "unverified"


def test_feature_declaration_does_not_claim_service_acceptance():
    declared = replace(DEFAULT_PROFILE, inheritance=True)
    assert declared.to_dict()["service_acceptance"] == "unverified"
