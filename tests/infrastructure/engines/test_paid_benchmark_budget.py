# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.infrastructure.engines.paid_benchmark_budget import (
    PaidBenchmarkBudget,
    PaidBenchmarkBudgetStore,
)


def test_budget_authorizes_only_within_remaining_cap() -> None:
    budget = PaidBenchmarkBudget(spent_usd=19.0)
    assert budget.authorize(1.0)
    assert not budget.authorize(1.01)
    assert budget.charge(1.0).spent_usd == 20.0


def test_budget_rejects_invalid_charges() -> None:
    with pytest.raises(ValueError):
        PaidBenchmarkBudget().charge(20.01)
    with pytest.raises(ValueError):
        PaidBenchmarkBudget().charge(-1)


def test_store_recovers_and_persists_spend(tmp_path) -> None:
    store = PaidBenchmarkBudgetStore(tmp_path / "budget.json")
    assert store.load().spent_usd == 0
    store.charge(3.5)
    assert store.load().spent_usd == 3.5
    (tmp_path / "budget.json").write_text("invalid", encoding="utf-8")
    assert store.load().spent_usd == 0


def test_store_rejects_negative_cap(tmp_path) -> None:
    with pytest.raises(ValueError):
        PaidBenchmarkBudgetStore(tmp_path / "budget.json", cap_usd=-1.0)
