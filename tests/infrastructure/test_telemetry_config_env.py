# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[telemetry] max_spans` / `max_samples` from the environment: a pod with no vibey.toml
must be able to bound the in-process telemetry buffers (doctrine 12.c)."""

from __future__ import annotations

import pytest

from vibey.domain.config import (
    DEFAULT_TELEMETRY_MAX_SAMPLES,
    DEFAULT_TELEMETRY_MAX_SPANS,
    ConfigError,
    load_config_from_string,
)
from vibey.infrastructure.config_loader import apply_env_overrides, load_config_from_environment

_PROJECT = '[project]\nname = "x"\n'
_CASES = [
    ("VIBEY_TELEMETRY_MAX_SPANS", "max_spans"),
    ("VIBEY_TELEMETRY_MAX_SAMPLES", "max_samples"),
]


@pytest.mark.parametrize(("variable", "key"), _CASES)
def test_the_environment_alone_sets_the_cap(variable: str, key: str) -> None:
    config = load_config_from_environment({variable: "42"})
    assert getattr(config.telemetry, key) == 42


def test_an_environment_with_neither_variable_keeps_the_defaults() -> None:
    config = load_config_from_environment({})
    assert config.telemetry.max_spans == DEFAULT_TELEMETRY_MAX_SPANS
    assert config.telemetry.max_samples == DEFAULT_TELEMETRY_MAX_SAMPLES


@pytest.mark.parametrize(("variable", "key"), _CASES)
def test_the_environment_beats_the_file(variable: str, key: str) -> None:
    data = {"project": {"name": "x"}, "telemetry": {key: 7}}
    apply_env_overrides(data, {variable: "30"})
    assert data["telemetry"] == {key: 30}


@pytest.mark.parametrize(("variable", "key"), _CASES)
@pytest.mark.parametrize("value", ["abc", "true", "1.5"])
def test_a_non_integer_environment_value_is_refused(variable: str, key: str, value: str) -> None:
    with pytest.raises(ValueError, match=f"{variable} must be an integer"):
        apply_env_overrides({}, {variable: value})


@pytest.mark.parametrize(("variable", "key"), _CASES)
@pytest.mark.parametrize("value", ["0", "-5"])
def test_a_non_positive_environment_value_is_refused_by_the_config(
    variable: str, key: str, value: str
) -> None:
    with pytest.raises(ConfigError) as error:
        load_config_from_environment({variable: value})
    assert f"telemetry.{key}" in str(error.value)


@pytest.mark.parametrize(("variable", "key"), _CASES)
def test_an_empty_environment_value_is_ignored(variable: str, key: str) -> None:
    data: dict[str, object] = {}
    apply_env_overrides(data, {variable: "  "})
    assert "telemetry" not in data
    assert load_config_from_string(_PROJECT).telemetry.max_spans == DEFAULT_TELEMETRY_MAX_SPANS
