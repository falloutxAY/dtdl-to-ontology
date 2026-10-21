import hashlib
import io
import zipfile

import pytest

from tools.fetch_willow import PREFIX, unpack


def archive_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(PREFIX + "LICENSE", "fixture test license")
        archive.writestr(PREFIX + "Ontology/Willow/A.json", "{}")
        archive.writestr(PREFIX + "Metadata/Willow.Ontology.DTDLv3.jsonld", "[]")
    return buffer.getvalue()


def test_checksum_and_source_only_extraction(tmp_path):
    data = archive_bytes()
    destination = tmp_path / "fixture"
    manifest = unpack(data, destination, hashlib.sha256(data).hexdigest())
    assert (destination / "LICENSE").exists()
    assert (destination / "Ontology/Willow/A.json").exists()
    assert not (destination / "Metadata").exists()
    assert "Ontology/Willow/A.json" in manifest["files"]


def test_checksum_failure_does_not_extract(tmp_path):
    destination = tmp_path / "fixture"
    with pytest.raises(ValueError, match="checksum mismatch"):
        unpack(archive_bytes(), destination)
    assert not destination.exists()
