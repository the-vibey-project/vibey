# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibey_gh.delivery_estimate import (
    BillingUsage,
    CommitObservation,
    DeliveryEstimator,
    DeliveryForecast,
    IssueObservation,
    PhiConfig,
    PullRequestObservation,
    WorkHistory,
    WorkHistoryCalculator,
    _number,
)
from vibey_gh.delivery_sources import DeliverySourceSnapshot
from vibey_gh.estimation import TrackRecord
from vibey_gh.feasibility import Coordinate, StateVector
from vibey_gh.interfaces.delivery_estimate_interface import (
    BillingForecastInterface,
    BillingUsageInterface,
    DeliveryEstimatorInterface,
    DeliveryForecastInterface,
    DeliveryHistoryCalculatorInterface,
    DeliveryTrackRecordInterface,
    PhiConfigInterface,
    WorkHistoryInterface,
)


def _snapshot() -> DeliverySourceSnapshot:
    return DeliverySourceSnapshot(
        issues=(
            IssueObservation(1, "OPEN", labels=("size/M",)),
            IssueObservation(2, "CLOSED"),
        ),
        pull_requests=(
            PullRequestObservation(3, "OPEN", labels=("size/S",)),
            PullRequestObservation(4, "MERGED", "2026-09-18T00:00:00+00:00", ("size/L",)),
            PullRequestObservation(5, "MERGED", "2026-09-19T00:00:00+00:00", ("size/XL",)),
            PullRequestObservation(6, "MERGED", "not-a-date", ("size/S",)),
        ),
        commits=(
            CommitObservation("a", "2026-09-18T00:00:00+00:00"),
            CommitObservation("b", "2026-09-18T01:00:00+00:00"),
            CommitObservation("c", "2026-09-19T00:00:00+00:00"),
            CommitObservation("bad", "not-a-date"),
        ),
        source_revision="abc",
    )


def _full_usage() -> BillingUsage:
    return BillingUsage(
        elapsed_seconds=86_400.0,
        dollars=12.0,
        turn_completed_events=2,
        budget_turns=3,
        ledger_events=4,
        phase_transition_events=2,
        capacity_rejections=0,
        handoffs=1,
        tool_invocations=4,
        file_edits=2,
        artifacts_produced=1,
    )


def _history(
    *,
    remaining: float = 4.0,
    completed: float = 18.0,
    mean: float | None = 9.0,
    median: float | None = 9.0,
) -> WorkHistory:
    return WorkHistory(
        issue_count=1,
        open_issue_count=1,
        open_pull_request_count=1,
        merged_pull_request_count=2,
        commit_count=4,
        open_issue_units=3.0,
        open_pull_request_units=1.0,
        remaining_units=remaining,
        completed_units=completed,
        active_commit_days=2,
        active_merge_days=2,
        mean_units_per_merge_day=mean,
        median_units_per_merge_day=median,
        mean_commits_per_active_day=2.0,
        median_commits_per_active_day=2.0,
    )


def test_history_statistics_weight_open_and_completed_work() -> None:
    calculator = WorkHistoryCalculator()
    history = calculator.calculate(_snapshot())
    assert isinstance(calculator, DeliveryHistoryCalculatorInterface)
    assert isinstance(history, WorkHistoryInterface)
    assert history.issue_count == 2
    assert history.open_issue_count == 1
    assert history.open_pull_request_count == 1
    assert history.merged_pull_request_count == 3
    assert history.commit_count == 4
    assert history.remaining_units == 4.0
    assert history.completed_units == 19.0
    assert history.active_merge_days == 2
    assert history.mean_units_per_merge_day == 9.0
    assert history.median_units_per_merge_day == 9.0
    assert history.mean_commits_per_active_day == 2.0
    assert history.median_commits_per_active_day == 1.5
    assert history.as_dict()["work_units"] == {"remaining": 4.0, "completed": 19.0}


def test_history_empty_or_invalid_dates_have_unknown_rates() -> None:
    history = WorkHistoryCalculator().calculate(DeliverySourceSnapshot())
    assert history.remaining_units == 0
    assert history.completed_units == 0
    assert history.mean_units_per_merge_day is None
    assert history.median_units_per_merge_day is None
    assert history.mean_commits_per_active_day is None
    assert history.median_commits_per_active_day is None
    assert WorkHistoryCalculator._day(None) is None
    with pytest.raises(ValueError, match="positive finite"):
        WorkHistoryCalculator((("s", 0.0),))


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"floor": -0.1}, "floor"),
        ({"floor": 1.0}, "floor"),
        ({"epsilon": 0.0}, "epsilon"),
        ({"exponent": 0.0}, "exponent"),
        ({"unknown_factor": 0.5}, "unknown phi"),
    ],
)
def test_phi_constants_are_explicitly_validated(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PhiConfig(**kwargs)


def test_forecast_dilates_measured_shortfalls_and_scales_all_billing_dimensions() -> None:
    state = StateVector.unknown().with_measurements(
        (
            Coordinate("hardware", "availability", 0.5, "test", 1.0),
            Coordinate("agency", "reliability", 0.2, "test", 1.0),
        )
    )
    phi = PhiConfig(floor=0.1, epsilon=0.01, exponent=1.0)
    estimator = DeliveryEstimator(phi=phi)
    assert isinstance(phi, PhiConfigInterface)
    forecast = estimator.calculate(
        _history(),
        _full_usage(),
        state=state,
        recorded_at="2026-09-19T00:00:00Z",
        source_fingerprint="fingerprint",
        assumptions=("operator assumption",),
    )
    assert isinstance(estimator, DeliveryEstimatorInterface)
    assert isinstance(forecast, DeliveryForecastInterface)
    assert isinstance(forecast.billing, BillingForecastInterface)
    assert isinstance(forecast.track_record, DeliveryTrackRecordInterface)
    assert forecast.time_days_low is not None and forecast.time_days_high is not None
    assert forecast.phi_product > 1.0
    assert forecast.first_repair[0] == "agency.reliability"
    assert forecast.billing.planned_low.dollars == 12.0 / 18.0 * 4.0
    assert forecast.billing.planned_low.budget_turns == 1
    assert forecast.billing.planned_low.elapsed_seconds is not None
    assert not forecast.billing.unknowns
    assert forecast.as_dict()["materials"]
    assert forecast.event_payload()["schema"] == "vibey-delivery-forecast/v1"
    assert any("operator assumption" in item for item in forecast.assumptions)
    assert any("billing actual" in line for line in forecast.lines())


def test_forecast_unknown_data_is_visible_and_zero_remaining_is_complete() -> None:
    estimator = DeliveryEstimator()
    unknown = estimator.calculate(
        _history(remaining=4.0, completed=0.0, mean=None, median=None),
        BillingUsage(),
        state=StateVector.unknown(),
        recorded_at="now",
        source_fingerprint="unknown",
    )
    assert unknown.time_days_low is None
    assert "elapsed_seconds: no historical throughput band" in unknown.billing.unknowns
    assert unknown.billing.planned_low.dollars is None
    complete = estimator.calculate(
        _history(remaining=0.0, completed=0.0, mean=None, median=None),
        BillingUsage(),
        state=StateVector.unknown(),
        recorded_at="now",
        source_fingerprint="complete",
    )
    assert complete.time_days_low == 0.0
    assert complete.billing.planned_low.as_dict() == {
        "elapsed_seconds": 0,
        "dollars": 0,
        "turn_completed_events": 0,
        "budget_turns": 0,
        "ledger_events": 0,
        "phase_transition_events": 0,
        "capacity_rejections": 0,
        "handoffs": 0,
        "tool_invocations": 0,
        "file_edits": 0,
        "artifacts_produced": 0,
    }


def test_forecast_grades_prior_per_unit_predictions_and_counts_ungraded() -> None:
    previous = {
        "history": {"work_units": {"remaining": 10, "completed": 0}},
        "billing": {
            "planned_low": {
                "elapsed_seconds": 100,
                "dollars": 20,
                "budget_turns": 20,
            },
            "actual": {"elapsed_seconds": 0, "dollars": 0, "budget_turns": 0},
        },
    }
    prior_invalid = {"history": {"work_units": {"remaining": "bad"}}}
    previous_no_completion = {
        "history": {"work_units": {"remaining": 10, "completed": 2}},
        "billing": {
            "planned_low": {"elapsed_seconds": 100, "dollars": 20},
            "actual": {"elapsed_seconds": 5, "dollars": 1},
        },
    }
    current = DeliveryEstimator().calculate(
        _history(remaining=8, completed=2),
        BillingUsage(elapsed_seconds=30, dollars=6, budget_turns=3),
        state=StateVector.unknown(),
        recorded_at="now",
        source_fingerprint="current",
        prior_records=(previous, prior_invalid, previous_no_completion),
    )
    assert current.track_record.time.graded == 1
    assert current.track_record.dollars.graded == 1
    assert current.track_record.time.ungraded == 2
    assert current.track_record.dollars.ungraded == 2
    assert current.track_record.dimensions["budget_turns"].graded == 1
    assert set(current.track_record.dimensions) == {
        "elapsed_seconds",
        "dollars",
        "turn_completed_events",
        "budget_turns",
        "ledger_events",
        "phase_transition_events",
        "capacity_rejections",
        "handoffs",
        "tool_invocations",
        "file_edits",
        "artifacts_produced",
    }


def test_interface_adapters_and_usage_edge_helpers_are_kept_covered() -> None:
    history = _history()
    usage = _full_usage()
    fields = (
        "issue_count",
        "open_issue_count",
        "open_pull_request_count",
        "merged_pull_request_count",
        "commit_count",
        "open_issue_units",
        "open_pull_request_units",
        "remaining_units",
        "completed_units",
        "active_commit_days",
        "active_merge_days",
        "mean_units_per_merge_day",
        "median_units_per_merge_day",
        "mean_commits_per_active_day",
        "median_commits_per_active_day",
    )
    fake_history = SimpleNamespace(**{field: getattr(history, field) for field in fields})
    fake_usage = SimpleNamespace(**usage.as_dict())
    converted = DeliveryEstimator().calculate(
        fake_history,
        fake_usage,
        state=StateVector.unknown(),
        recorded_at="now",
        source_fingerprint="converted",
    )
    assert converted.history == history
    assert converted.actual_usage == usage
    assert isinstance(history, WorkHistoryInterface)
    assert isinstance(usage, BillingUsageInterface)
    assert DeliveryEstimator._per_unit_seconds(BillingUsage(), _history()) is None
    assert DeliveryEstimator._per_unit_seconds(_full_usage(), _history(completed=0)) is None
    assert DeliveryEstimator._per_unit_seconds(_full_usage(), _history()) == 86400.0 / 18 * 4
    assert DeliveryEstimator._replace_elapsed(BillingUsage(), 5.0).elapsed_seconds == 5.0
    assert DeliveryEstimator._replace_elapsed(_full_usage(), 5.0) == _full_usage()
    assert "dollars=1.0–2.0" in DeliveryForecast._usage_line(
        BillingUsage(dollars=1.0), high=BillingUsage(dollars=2.0)
    )
    assert DeliveryEstimator._delta(None, 1.0) is None
    assert DeliveryEstimator._delta(1.0, None) is None
    assert _number(True) is None
    assert _number(float("nan")) is None
    assert TrackRecord(0, 0, None, None).mean_error is None


def test_prior_record_shape_and_missing_dimension_paths_are_explicit() -> None:
    assert (
        DeliveryEstimator._prior_values({"history": {"work_units": "bad"}, "billing": {}}) is None
    )
    assert (
        DeliveryEstimator._prior_values(
            {
                "history": {"work_units": {"remaining": "bad", "completed": 1}},
                "billing": {},
            }
        )
        is None
    )
    assert (
        DeliveryEstimator._prior_values(
            {
                "history": {"work_units": {"remaining": 1, "completed": 1}},
                "billing": {"planned_low": [], "actual": {}},
            }
        )
        is None
    )
    history = _history(remaining=8, completed=2)
    forecast = DeliveryEstimator().calculate(
        history,
        BillingUsage(elapsed_seconds=30, dollars=6),
        state=StateVector.unknown(),
        recorded_at="now",
        source_fingerprint="missing-dimensions",
        prior_records=(
            {
                "history": {"work_units": {"remaining": 10, "completed": 0}},
                "billing": {
                    "planned_low": {"elapsed_seconds": None, "dollars": 20},
                    "actual": {"elapsed_seconds": 0, "dollars": 0},
                },
            },
            {
                "history": {"work_units": {"remaining": 10, "completed": 0}},
                "billing": {
                    "planned_low": {"elapsed_seconds": 100, "dollars": None},
                    "actual": {"elapsed_seconds": 0, "dollars": 0},
                },
            },
        ),
    )
    assert forecast.track_record.time.ungraded == 1
    assert forecast.track_record.dollars.ungraded == 1
