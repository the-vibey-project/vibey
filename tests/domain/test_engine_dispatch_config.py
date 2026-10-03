# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[engines]`'s dispatch keys (ADR-0079): defaults, every key, and every refusal."""

from __future__ import annotations

import pytest

from vibey.domain.config import (
    DEFAULT_PAID_DAILY_CAP,
    ConfigError,
    EngineDispatchConfig,
    load_config_from_string,
)
from vibey.domain.interfaces.config_interface import EngineDispatchConfigInterface


def test_the_defaults_are_auto_with_a_bounded_overflow() -> None:
    config = EngineDispatchConfig.from_data({})
    assert config == EngineDispatchConfig()
    assert isinstance(config, EngineDispatchConfigInterface)
    assert config.mode == "auto"
    assert config.overflow_after_seconds == 600
    assert config.paid_daily_cap == DEFAULT_PAID_DAILY_CAP == 10
    assert config.slot_poll_seconds == 30
    assert dict(config.slots) == {}
    assert (config.auto_window_hours, config.auto_min_sessions) == (168, 20)
    assert (config.auto_min_contention, config.auto_max_age_hours) == (0.25, 24)


def test_a_kubernetes_allow_list_configures_no_dispatch() -> None:
    assert EngineDispatchConfig.from_data({"engines": ["claudeloop"]}) == EngineDispatchConfig()


def test_every_key_is_read() -> None:
    config = EngineDispatchConfig.from_data(
        {
            "engines": {
                "mode": "hybrid",
                "overflow_after_seconds": 0,
                "paid_daily_cap": 0,
                "slot_poll_seconds": 5,
                "slots": {"gptossloop": 2, "claudeloop": 1},
                "auto_window_hours": 24,
                "auto_min_sessions": 1,
                "auto_min_contention": 1,
                "auto_max_age_hours": 2,
                "enabled": ["claudeloop"],
            }
        }
    )
    assert config == EngineDispatchConfig(
        mode="hybrid",
        overflow_after_seconds=0,
        paid_daily_cap=0,
        slot_poll_seconds=5,
        slots={"gptossloop": 2, "claudeloop": 1},
        auto_window_hours=24,
        auto_min_sessions=1,
        auto_min_contention=1.0,
        auto_max_age_hours=2,
    )


@pytest.mark.parametrize(
    ("table", "path"),
    [
        ({"mode": "multiplexer"}, "engines.mode"),
        ({"mode": 1}, "engines.mode"),
        ({"paid_daily_cap": -1}, "engines.paid_daily_cap"),
        ({"paid_daily_cap": True}, "engines.paid_daily_cap"),
        ({"paid_daily_cap": 1.5}, "engines.paid_daily_cap"),
        ({"overflow_after_seconds": -1}, "engines.overflow_after_seconds"),
        ({"slot_poll_seconds": 0}, "engines.slot_poll_seconds"),
        ({"auto_window_hours": 0}, "engines.auto_window_hours"),
        ({"auto_min_sessions": 0}, "engines.auto_min_sessions"),
        ({"auto_max_age_hours": 0}, "engines.auto_max_age_hours"),
        ({"auto_min_contention": 1.5}, "engines.auto_min_contention"),
        ({"auto_min_contention": -0.1}, "engines.auto_min_contention"),
        ({"auto_min_contention": True}, "engines.auto_min_contention"),
        ({"auto_min_contention": "half"}, "engines.auto_min_contention"),
        ({"slots": ["gptossloop"]}, "engines.slots"),
        ({"slots": {"martian": 1}}, "engines.slots"),
        ({"slots": {"gptossloop": 0}}, "engines.slots.gptossloop"),
        ({"slots": {"gptossloop": True}}, "engines.slots.gptossloop"),
    ],
)
def test_a_bad_key_is_refused_by_its_path(table: dict[str, object], path: str) -> None:
    with pytest.raises(ConfigError) as caught:
        EngineDispatchConfig.from_data({"engines": table})
    assert caught.value.path == path


def test_engines_that_is_neither_a_table_nor_a_list_is_refused() -> None:
    with pytest.raises(ConfigError, match="engines"):
        EngineDispatchConfig.from_data({"engines": "claudeloop"})


def test_a_whole_vibey_toml_carries_the_dispatch_keys() -> None:
    config = load_config_from_string(
        '[project]\nname = "p"\n\n[engines]\nmode = "singleton"\npaid_daily_cap = 3\n'
        "\n[engines.slots]\ngptossloop = 2\n"
    )
    assert config.engine_dispatch.mode == "singleton"
    assert config.engine_dispatch.paid_daily_cap == 3
    assert dict(config.engine_dispatch.slots) == {"gptossloop": 2}
