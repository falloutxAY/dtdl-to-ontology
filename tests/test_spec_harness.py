import hashlib
import json

import pytest

from tools.check_spec import check

from .conftest import interface


def test_upstream_inputs_are_separate_documents_and_unsupported_is_not_a_pass(tmp_path):
    models = [
        {"input": [[interface()]], "valid": True},
        {"input": [interface("A"), interface("B")], "valid": True},
        {"input": [{"@type": "Interface"}], "valid": False},
        {
            "input": [interface(**{"@context": ["dtmi:dtdl:context;3", "dtmi:example:unknown;1"]})],
            "valid": True,
        },
        {"input": [interface("ValidButExpectedInvalid")], "valid": False},
    ]
    data = json.dumps(models).encode()
    (tmp_path / "cases.json").write_bytes(data)
    (tmp_path / "fixture.json").write_text(
        json.dumps(
            {
                "repository": "test",
                "revision": "test",
                "files": {"cases.json": hashlib.sha256(data).hexdigest()},
            }
        )
    )
    report = check(tmp_path)
    assert report["cases"] == 5
    assert report["counts"] == {"matched": 3, "unsupported_extension": 1, "disagreed": 1}
    (tmp_path / "cases.json").write_text("[]")
    with pytest.raises(ValueError, match="Fixture changed"):
        check(tmp_path)
