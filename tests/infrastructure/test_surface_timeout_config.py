# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[surfaces] adapter_timeout_seconds`: the declared bound on a surface adapter's network calls (#726)."""

from __future__ import annotations

import pytest

from vibey.domain.config import (
    DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS,
    ConfigError,
    SurfacesConfig,
    load_config_from_string,
)
from vibey.domain.interfaces.config_interface import SurfacesConfigInterface
from vibey.infrastructure.config_loader import apply_env_overrides

_PROJECT = '[project]\nname = "x"\n'


def test_the_adapter_timeout_defaults_to_ten_seconds() -> None:
    config = load_config_from_string(_PROJECT)
    assert config.surfaces.adapter_timeout_seconds == 10
    assert DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS == 10


def test_the_adapter_timeout_is_read_from_the_surfaces_table() -> None:
    config = load_config_from_string(_PROJECT + "[surfaces]\nadapter_timeout_seconds = 7\n")
    assert config.surfaces.adapter_timeout_seconds == 7


@pytest.mark.parametrize("value", ["0", "601", "true", '"7"', "7.5"])
def test_the_adapter_timeout_rejects_out_of_range_and_non_integer_values(value: str) -> None:
    with pytest.raises(ConfigError) as error:
        load_config_from_string(_PROJECT + f"[surfaces]\nadapter_timeout_seconds = {value}\n")
    assert "surfaces.adapter_timeout_seconds" in str(error.value)
    assert "must be an integer from 1 to 600" in str(error.value)


def test_the_environment_beats_the_file() -> None:
    data = {"project": {"name": "x"}, "surfaces": {"adapter_timeout_seconds": 7}}
    apply_env_overrides(data, {"VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS": "30"})
    assert data["surfaces"] == {"adapter_timeout_seconds": 30}


def test_a_non_integer_environment_value_is_refused() -> None:
    with pytest.raises(
        ValueError, match="VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS must be an integer"
    ):
        apply_env_overrides({}, {"VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS": "abc"})


def test_an_empty_environment_value_is_ignored() -> None:
    data: dict[str, object] = {}
    apply_env_overrides(data, {"VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS": ""})
    assert "surfaces" not in data


def test_the_surfaces_config_satisfies_its_interface() -> None:
    assert isinstance(SurfacesConfig(), SurfacesConfigInterface)
    assert isinstance(load_config_from_string(_PROJECT).surfaces, SurfacesConfigInterface)
