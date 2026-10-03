# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[engines]`'s dispatch keys from vibey.toml, the project record and the environment
(ADR-0079)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibey.domain.config import ConfigError, EngineDispatchConfig
from vibey.infrastructure.config_loader import (
    ENGINE_DISPATCH_CONFIG,
    EngineDispatchConfigLoader,
    load_config_from_path,
    load_runtime_config_from_path,
)
from vibey.infrastructure.interfaces.class_contracts import EngineDispatchConfigLoaderInterface


def test_the_loader_satisfies_its_seam() -> None:
    assert isinstance(ENGINE_DISPATCH_CONFIG, EngineDispatchConfigLoader)
    assert isinstance(ENGINE_DISPATCH_CONFIG, EngineDispatchConfigLoaderInterface)


def test_the_record_is_read_and_the_environment_beats_it() -> None:
    stored = {"engines": {"mode": "hybrid", "paid_daily_cap": 5, "slots": {"gptossloop": 2}}}
    config = ENGINE_DISPATCH_CONFIG.load(
        stored,
        {
            "VIBEY_ENGINES_PAID_DAILY_CAP": "2",
            "VIBEY_ENGINES_OVERFLOW_AFTER_SECONDS": "90",
            "VIBEY_ENGINES_MODE": "singleton",
        },
    )
    assert config == EngineDispatchConfig(
        mode="singleton", overflow_after_seconds=90, paid_daily_cap=2, slots={"gptossloop": 2}
    )
    assert stored["engines"]["mode"] == "hybrid", "the record itself is never rewritten"


def test_a_kubernetes_allow_list_record_still_takes_the_environment() -> None:
    config = ENGINE_DISPATCH_CONFIG.load(
        {"engines": ["claudeloop"]}, {"VIBEY_ENGINES_MODE": "hybrid"}
    )
    assert config.mode == "hybrid"


def test_no_record_and_no_environment_is_every_default() -> None:
    assert ENGINE_DISPATCH_CONFIG.load({}, {}) == EngineDispatchConfig()


def test_an_unrelated_malformed_variable_never_stops_dispatch() -> None:
    config = ENGINE_DISPATCH_CONFIG.load({}, {"VIBEY_EMAIL_SMTP_PORT": "not a port"})
    assert config == EngineDispatchConfig()


def test_a_malformed_dispatch_variable_is_refused() -> None:
    with pytest.raises(ValueError, match="VIBEY_ENGINES_PAID_DAILY_CAP"):
        ENGINE_DISPATCH_CONFIG.load({}, {"VIBEY_ENGINES_PAID_DAILY_CAP": "unlimited"})
    with pytest.raises(ConfigError, match="engines.paid_daily_cap"):
        ENGINE_DISPATCH_CONFIG.load({}, {"VIBEY_ENGINES_PAID_DAILY_CAP": "-1"})


def test_vibey_new_copies_only_the_dispatch_keys_of_engines(tmp_path: Path) -> None:
    path = tmp_path / "vibey.toml"
    path.write_text(
        '[project]\nname = "p"\n\n[engines]\nenabled = ["claudeloop"]\nmode = "hybrid"\n'
        "paid_daily_cap = 4\n\n[engines.slots]\ngptossloop = 2\n"
    )
    assert load_runtime_config_from_path(path) == {
        "engines": {"mode": "hybrid", "paid_daily_cap": 4, "slots": {"gptossloop": 2}}
    }


def test_an_engines_table_without_dispatch_keys_copies_nothing(tmp_path: Path) -> None:
    path = tmp_path / "vibey.toml"
    path.write_text('[project]\nname = "p"\n\n[engines]\nenabled = ["claudeloop"]\n')
    assert load_runtime_config_from_path(path) == {}


def test_a_bad_dispatch_key_is_refused_at_vibey_new(tmp_path: Path) -> None:
    path = tmp_path / "vibey.toml"
    path.write_text('[project]\nname = "p"\n\n[engines]\nmode = "multiplexer"\n')
    with pytest.raises(ConfigError, match="engines.mode"):
        load_runtime_config_from_path(path)


def test_a_whole_vibey_toml_takes_the_dispatch_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "vibey.toml"
    path.write_text('[project]\nname = "p"\n\n[engines]\npaid_daily_cap = 4\n')
    monkeypatch.setenv("VIBEY_ENGINES_PAID_DAILY_CAP", "1")
    assert load_config_from_path(path).engine_dispatch.paid_daily_cap == 1
