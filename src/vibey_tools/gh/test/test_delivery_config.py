# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

import math
from pathlib import Path

import pytest

from vibey_gh.config import EstimateConfig, load_config


def test_forecast_config_is_loaded_as_a_generic_nested_table(tmp_path: Path) -> None:
    (tmp_path / ".vibey-gh.toml").write_text(
        """
[estimate.forecast]
ledger = "archive/estimates.jsonl"
report = "reports/estimate.md"
billing_ledger = "archive/billing.jsonl"
phi_floor = 0.2
phi_epsilon = 0.03
phi_exponent = 1.5
unknown_factor = 1.2
[estimate.forecast.size_weights]
tiny = 0.25
normal = 2.0
""",
        encoding="utf-8",
    )
    config = load_config(tmp_path).estimate
    assert config.forecast_ledger == "archive/estimates.jsonl"
    assert config.forecast_report == "reports/estimate.md"
    assert config.forecast_billing_ledger == "archive/billing.jsonl"
    assert config.forecast_phi_floor == 0.2
    assert config.forecast_phi_epsilon == 0.03
    assert config.forecast_phi_exponent == 1.5
    assert config.forecast_phi_unknown_factor == 1.2
    assert config.forecast_size_weights == (("tiny", 0.25), ("normal", 2.0))


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("forecast_ledger", "", "ledger and report"),
        ("forecast_report", "", "ledger and report"),
        ("forecast_billing_ledger", "", "billing ledger"),
        ("forecast_phi_floor", -0.1, "phi_floor"),
        ("forecast_phi_floor", 1.0, "phi_floor"),
        ("forecast_phi_floor", True, "finite number"),
        ("forecast_phi_floor", math.inf, "finite number"),
        ("forecast_phi_epsilon", True, "finite number"),
        ("forecast_phi_epsilon", math.nan, "finite number"),
        ("forecast_phi_epsilon", 0.0, "epsilon"),
        ("forecast_phi_exponent", math.inf, "finite number"),
        ("forecast_phi_exponent", 0.0, "exponent"),
        ("forecast_phi_unknown_factor", math.nan, "finite number"),
        ("forecast_phi_unknown_factor", 0.5, "unknown_factor"),
        ("forecast_size_weights", (("s", 1.0), ("s", 2.0)), "size_weights"),
        ("forecast_size_weights", (("s", True),), "finite number"),
        ("forecast_size_weights", (("s", math.inf),), "finite number"),
        ("forecast_size_weights", (("s", 0.0),), "size_weights values"),
    ],
)
def test_forecast_config_rejects_invalid_materials(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        EstimateConfig(**{field: value})


def test_forecast_config_rejects_non_tables() -> None:
    with pytest.raises(TypeError, match="forecast must be a table"):
        EstimateConfig.from_table({"forecast": "bad"})
    with pytest.raises(TypeError, match="size_weights must be a table"):
        EstimateConfig.from_table({"forecast": {"size_weights": "bad"}})


@pytest.mark.parametrize("key, value", [("phi_floor", True), ("phi_epsilon", math.inf)])
def test_forecast_table_rejects_bool_and_non_finite_numbers(key: str, value: object) -> None:
    with pytest.raises(ValueError, match="finite number"):
        EstimateConfig.from_table({"forecast": {key: value}})
