import json

import pytest


def interface(name="Example", contents=None, **fields):
    return {
        "@id": f"dtmi:example:{name};1",
        "@type": "Interface",
        "@context": "dtmi:dtdl:context;3",
        "contents": contents or [],
        **fields,
    }


@pytest.fixture
def write_models(tmp_path):
    def write(*models):
        path = tmp_path / "models.json"
        path.write_text(json.dumps(list(models)), encoding="utf-8")
        return path

    return write
