import json

import pytest
from exporter.cli import run
from exporter.registry import FormatRegistry, default_registry
from exporter.render import render_csv, render_json, render_markdown

ROWS = [{"name": "Ann", "team": "x"}, {"name": "Bo", "team": "y|z"}]


def test_register_and_get_case_insensitive() -> None:
    registry = FormatRegistry()
    registry.register("Upper", lambda rows: "U")
    assert registry.get("UPPER")([]) == "U"
    assert "upper" in registry
    assert "UPPER" in registry
    assert "other" not in registry


def test_duplicate_registration_rejected() -> None:
    registry = FormatRegistry()
    registry.register("a", lambda rows: "1")
    with pytest.raises(ValueError):
        registry.register("A", lambda rows: "2")
    assert registry.get("a")([]) == "1"


def test_replace_overrides() -> None:
    registry = FormatRegistry()
    registry.register("a", lambda rows: "1")
    registry.register("a", lambda rows: "2", replace=True)
    assert registry.get("a")([]) == "2"


def test_unknown_name_raises_key_error() -> None:
    with pytest.raises(KeyError):
        FormatRegistry().get("nope")


def test_names_sorted() -> None:
    registry = FormatRegistry()
    for name in ["zeta", "Alpha", "mid"]:
        registry.register(name, lambda rows: "")
    assert registry.names() == ["alpha", "mid", "zeta"]


def test_default_registry_contents() -> None:
    assert default_registry().names() == ["csv", "json", "md"]


def test_default_registry_is_new_each_call() -> None:
    first = default_registry()
    first.register("extra", lambda rows: "")
    assert "extra" not in default_registry()


def test_markdown_rendering() -> None:
    assert render_markdown(ROWS) == (
        "| name | team |\n| --- | --- |\n| Ann | x |\n| Bo | y\\|z |\n"
    )


def test_markdown_empty_and_missing_keys() -> None:
    assert render_markdown([]) == ""
    out = render_markdown([{"a": "1", "b": "2"}, {"a": "3"}])
    assert out.splitlines()[-1] == "| 3 |  |"


def test_run_default_is_json() -> None:
    assert run([], ROWS) == (0, render_json(ROWS))
    assert json.loads(run([], ROWS)[1]) == ROWS


def test_run_csv_and_md() -> None:
    assert run(["--format", "CSV"], ROWS) == (0, render_csv(ROWS))
    assert run(["--format", "md"], ROWS) == (0, render_markdown(ROWS))


def test_run_unknown_format() -> None:
    assert run(["--format", "XML"], ROWS) == (2, "unknown format: xml\n")


def test_run_missing_value() -> None:
    assert run(["--format"], ROWS) == (2, "usage: --format NAME\n")


def test_run_uses_supplied_registry() -> None:
    registry = default_registry()
    registry.register("count", lambda rows: f"{len(rows)} rows\n")
    assert run(["--format", "count"], ROWS, registry) == (0, "2 rows\n")
    assert run(["--format", "count"], ROWS) == (2, "unknown format: count\n")


def test_run_custom_registry_can_replace_builtin() -> None:
    registry = default_registry()
    registry.register("json", lambda rows: "custom\n", replace=True)
    assert run([], ROWS, registry) == (0, "custom\n")
