import json

import pytest

from dtdl_to_ontology.loader import json_bounds, load, read_json

from .conftest import interface


def test_directory_and_collection_agree(tmp_path, write_models):
    models = [interface("B"), interface("A")]
    array = load(write_models(*models))
    folder = tmp_path / "source"
    folder.mkdir()
    for index, model in enumerate(models):
        (folder / f"{index}.json").write_text(json.dumps(model), encoding="utf-8")
    directory = load(folder)
    assert array.models.keys() == directory.models.keys()
    assert [m.raw for m in array.models.values()] == [m.raw for m in directory.models.values()]
    assert array.models["dtmi:example:A;1"].source.pointer == "/1"
    assert not directory.findings


@pytest.mark.parametrize(
    "text,code",
    [
        ("{", "INPUT"),
        ('{"a":1,"a":2}', "INPUT"),
        ("NaN", "INPUT"),
        (json.dumps(interface(**{"@context": "dtmi:dtdl:context;2"})), "VERSION"),
        (json.dumps(interface(**{"@id": "not-a-dtmi"})), "IDENTIFIER"),
    ],
)
def test_invalid_input_is_reported(tmp_path, text, code):
    path = tmp_path / "input.json"
    path.write_text(text, encoding="utf-8")
    result = load(path)
    assert result.findings[0].code == code
    assert result.findings[0].source.file == "input.json"
    assert result.findings[0].blocking


def test_conflicting_duplicate_identifies_both_locations(write_models):
    result = load(write_models(interface(), interface(description="different")))
    finding = result.findings[0]
    assert finding.code == "DUPLICATE_ID"
    assert finding.source.pointer == "/1"
    assert "/0" in finding.message


def test_duplicate_identical_keeps_all_sources(write_models):
    result = load(write_models(interface(), interface()))
    assert not result.findings
    assert len(next(iter(result.models.values())).sources) == 2


def test_input_depth_is_bounded():
    with pytest.raises(ValueError, match="bounds"):
        json_bounds([[[[1]]]], max_depth=3)


def test_numeric_overflow_cannot_escape_strict_json_loading():
    with pytest.raises(ValueError, match="finite range"):
        read_json(b'{"value": 1e999}')
