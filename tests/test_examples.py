from pathlib import Path

import pytest

from .test_cli import run_cli

EXAMPLES = Path(__file__).parents[1] / "examples"


@pytest.mark.parametrize(
    "filename,extra",
    [
        ("scalars.json", []),
        ("relationships.json", []),
        ("multiple-inheritance.json", ["--compatibility", "--policy", "flatten-inheritance"]),
        (
            "edge-properties.json",
            ["--compatibility", "--policy", "reify-relationship-properties"],
        ),
        ("minimal.json", ["--compatibility", "--policy", "json-objects"]),
        (
            "projection.json",
            [
                "--compatibility",
                "--policy",
                "flatten-inheritance",
                "--policy",
                "component-properties",
                "--policy",
                "json-collections",
                "--policy",
                "json-objects",
                "--policy",
                "enum-underlying",
                "--policy",
                "metadata-semantics",
            ],
        ),
        ("inheritance.json", ["--config", EXAMPLES / "native.json"]),
    ],
)
def test_readme_conversion_examples_are_executable(filename, extra, tmp_path):
    result = run_cli(
        "convert",
        EXAMPLES / filename,
        "--name",
        "Example",
        "--output",
        tmp_path / "result",
        *extra,
        "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "result" / "definition.json").exists()


def test_documented_strict_projection_failure_publishes_only_diagnostics(tmp_path):
    destination = tmp_path / "blocked"
    result = run_cli(
        "convert",
        EXAMPLES / "projection.json",
        "--name",
        "Blocked",
        "--output",
        destination,
    )
    assert result.returncode == 1
    assert (destination / "report.json").exists()
    assert not (destination / "definition.json").exists()
