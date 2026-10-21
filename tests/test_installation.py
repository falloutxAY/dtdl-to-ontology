import base64
import json
import os
import subprocess
import sys
import venv
from pathlib import Path

from .conftest import interface


def test_offline_wheel_install_runs_outside_checkout(tmp_path):
    repository = Path(__file__).parents[1]
    outside = tmp_path / "outside"
    outside.mkdir()
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    environment["PYTHONNOUSERSITE"] = "1"

    def run(*args):
        return subprocess.run(
            list(map(str, args)),
            cwd=outside,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=120,
        )

    wheels = tmp_path / "wheels"
    built = run(
        sys.executable,
        "-I",
        "-m",
        "pip",
        "--isolated",
        "wheel",
        "--no-deps",
        "--no-build-isolation",
        "--no-index",
        "--disable-pip-version-check",
        "--wheel-dir",
        wheels,
        repository,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    (wheel,) = wheels.glob("*.whl")
    isolated = tmp_path / "isolated"
    venv.EnvBuilder(with_pip=True).create(isolated)
    scripts = isolated / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    console = scripts / ("dtdl-to-ontology.exe" if os.name == "nt" else "dtdl-to-ontology")
    installed = run(
        python,
        "-I",
        "-m",
        "pip",
        "--isolated",
        "install",
        "--no-index",
        "--no-deps",
        "--disable-pip-version-check",
        wheel,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    imported = run(
        python,
        "-I",
        "-c",
        "import dtdl_to_ontology; print(dtdl_to_ontology.__file__)",
    )
    assert imported.returncode == 0, imported.stderr
    assert Path(imported.stdout.strip()).is_relative_to(isolated)
    assert run(console, "--version").returncode == 0
    source = outside / "source.json"
    source.write_text(
        json.dumps(
            interface(contents=[{"@type": "Property", "name": "label", "schema": "string"}])
        ),
        encoding="utf-8",
    )
    destination = outside / "converted"
    success = run(
        console,
        "convert",
        source,
        "--name",
        "Installed",
        "--output",
        destination,
        "--json",
    )
    assert success.returncode == 0, success.stdout + success.stderr
    report = json.loads(success.stdout)
    assert report["emission_status"] == "locally_validated"
    assert report["service_acceptance"] == "unverified"
    assert report["runtime_data_bindings"] == "not_generated"
    definition = json.loads((destination / "definition.json").read_text(encoding="utf-8"))
    for part in definition["parts"]:
        assert part["payloadType"] == "InlineBase64"
        decoded = base64.b64decode(part["payload"], validate=True)
        assert decoded.decode("utf-8")
        assert destination.joinpath("parts", *part["path"].split("/")).read_bytes() == decoded
    invalid = outside / "invalid.json"
    invalid.write_text(
        json.dumps(
            {
                "@context": "dtmi:dtdl:context;3",
                "@id": "dtmi:example:Invalid;1",
                "@type": "Interface",
                "contents": [
                    {
                        "@type": "Property",
                        "name": "state",
                        "schema": {
                            "@type": "Enum",
                            "valueSchema": "string",
                            "enumValues": [{"name": "On"}],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    blocked = outside / "blocked"
    failure = run(
        console,
        "convert",
        invalid,
        "--name",
        "Blocked",
        "--output",
        blocked,
        "--compatibility",
        "--policy",
        "enum-underlying",
        "--json",
    )
    assert failure.returncode == 1, failure.stdout + failure.stderr
    assert any(
        f["code"] == "ENUM_VALUE" and f["blocking"] for f in json.loads(failure.stdout)["findings"]
    )
    assert (blocked / "report.json").exists()
    assert not (blocked / "definition.json").exists()
