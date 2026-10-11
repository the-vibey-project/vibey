# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey new --accept-spec-json`: a spec that cannot be read leaves no project behind."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibey.cli import main as cli_main


def _new(*extra: str) -> object:
    return CliRunner().invoke(cli_main.app, ["new", "widget", "--ignore-sabbath", *extra])


def test_a_spec_file_that_is_not_there_is_a_usage_error_before_any_project_exists(
    tmp_path: Path,
) -> None:
    result = _new("--repo", str(tmp_path), "--accept-spec-json", str(tmp_path / "no.json"))

    assert result.exit_code == cli_main.EXIT_USAGE  # type: ignore[attr-defined]
    assert "--accept-spec-json" in result.output  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "content",
    ["{not json", "[]", '{"objective": "x"}'],
    ids=["malformed", "not-an-object", "missing-keys"],
)
def test_a_spec_that_does_not_parse_as_a_spec_is_a_usage_error(
    tmp_path: Path, content: str
) -> None:
    spec = tmp_path / "spec.json"
    spec.write_text(content)

    result = _new("--repo", str(tmp_path), "--accept-spec-json", str(spec))

    assert result.exit_code == cli_main.EXIT_USAGE  # type: ignore[attr-defined]
    assert "--accept-spec-json" in result.output  # type: ignore[attr-defined]
