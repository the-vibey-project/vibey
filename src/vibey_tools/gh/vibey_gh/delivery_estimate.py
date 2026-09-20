# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The continuous delivery forecast: time, cost and the material state.

This module is the executable form of the paper's calculus.  It keeps three
things separate so a useful number can never masquerade as a measurement:

* work history is calculated from issues, pull requests and commits;
* the billing snapshot is read from the conductor ledger, using the same
  dollars/turns vocabulary as the budget brake; and
* the forecast applies the configurable ``phi`` dilation to the 18-coordinate
  material state and records every assumption beside the result.

The calculator is pure.  GitHub, the local git history and JSONL ledgers are
read by the adapters in ``delivery_sources`` and ``estimate_ledger``.  That
split makes a forecast reproducible in a test or from an archived snapshot.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import TYPE_CHECKING, Final

from vibey_gh.estimation import Grade, GradedEstimator, Prediction, TrackRecord
from vibey_gh.feasibility import StateVector
from vibey_gh.interfaces.delivery_estimate_interface import (
    BillingForecastInterface,
    BillingUsageInterface,
    CommitObservationInterface,
    DeliveryEstimatorInterface,
    DeliveryForecastInterface,
    DeliveryHistoryCalculatorInterface,
    DeliverySourceSnapshotInterface,
    DeliveryTrackRecordInterface,
    IssueObservationInterface,
    PhiConfigInterface,
    PullRequestObservationInterface,
    WorkHistoryInterface,
)

if TYPE_CHECKING:
    from vibey_gh.feasibility import Coordinate

__all__ = [
    "BILLING_USAGE_FIELDS",
    "DEFAULT_SIZE_WEIGHTS",
    "BillingForecast",
    "BillingUsage",
    "CommitObservation",
    "DeliveryEstimator",
    "DeliveryForecast",
    "DeliveryTrackRecord",
    "IssueObservation",
    "PhiConfig",
    "PullRequestObservation",
    "WorkHistory",
    "WorkHistoryCalculator",
]


DEFAULT_SIZE_WEIGHTS: Final[tuple[tuple[str, float], ...]] = (
    ("xs", 0.5),
    ("s", 1.0),
    ("m", 3.0),
    ("l", 6.0),
    ("xl", 12.0),
)

BILLING_USAGE_FIELDS: Final[tuple[str, ...]] = (
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
)


@dataclass(frozen=True, slots=True)
class IssueObservation(IssueObservationInterface):
    number: int
    state: str
    is_pull_request: bool = False
    labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PullRequestObservation(PullRequestObservationInterface):
    number: int
    state: str
    merged_at: str | None = None
    labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CommitObservation(CommitObservationInterface):
    sha: str
    committed_at: str


@dataclass(frozen=True, slots=True)
class WorkHistory(WorkHistoryInterface):
    issue_count: int
    open_issue_count: int
    open_pull_request_count: int
    merged_pull_request_count: int
    commit_count: int
    open_issue_units: float
    open_pull_request_units: float
    remaining_units: float
    completed_units: float
    active_commit_days: int
    active_merge_days: int
    mean_units_per_merge_day: float | None
    median_units_per_merge_day: float | None
    mean_commits_per_active_day: float | None
    median_commits_per_active_day: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "issues": {
                "total": self.issue_count,
                "open": self.open_issue_count,
                "open_units": self.open_issue_units,
            },
            "pull_requests": {
                "open": self.open_pull_request_count,
                "merged": self.merged_pull_request_count,
                "open_units": self.open_pull_request_units,
            },
            "commits": {
                "total": self.commit_count,
                "active_days": self.active_commit_days,
                "mean_per_active_day": self.mean_commits_per_active_day,
                "median_per_active_day": self.median_commits_per_active_day,
            },
            "work_units": {
                "remaining": self.remaining_units,
                "completed": self.completed_units,
            },
            "throughput": {
                "active_merge_days": self.active_merge_days,
                "mean_units_per_merge_day": self.mean_units_per_merge_day,
                "median_units_per_merge_day": self.median_units_per_merge_day,
            },
        }


class WorkHistoryCalculator(DeliveryHistoryCalculatorInterface):
    """Turns forge observations into the work statistics the calculus consumes."""

    def __init__(self, size_weights: Sequence[tuple[str, float]] = DEFAULT_SIZE_WEIGHTS) -> None:
        weights = tuple((str(label).casefold(), float(value)) for label, value in size_weights)
        if not weights or any(value <= 0 or not math.isfinite(value) for _, value in weights):
            raise ValueError("size weights must contain positive finite values")
        self._weights = weights

    def calculate(self, snapshot: DeliverySourceSnapshotInterface) -> WorkHistory:
        issues = tuple(issue for issue in snapshot.issues if not issue.is_pull_request)
        open_issues = tuple(issue for issue in issues if issue.state.casefold() == "open")
        open_prs = tuple(pull for pull in snapshot.pull_requests if pull.state.casefold() == "open")
        merged = tuple(pull for pull in snapshot.pull_requests if pull.merged_at is not None)
        open_issue_units = sum(self._weight(issue.labels) for issue in open_issues)
        open_pr_units = sum(self._weight(pull.labels) for pull in open_prs)
        merged_units_by_day: dict[str, float] = {}
        for pull in merged:
            day = self._day(pull.merged_at)
            if day is not None:
                merged_units_by_day[day] = merged_units_by_day.get(day, 0.0) + self._weight(
                    pull.labels
                )
        commit_days = {
            day
            for commit in snapshot.commits
            if (day := self._day(commit.committed_at)) is not None
        }
        merge_rates = tuple(merged_units_by_day.values())
        commit_rates = (len(snapshot.commits) / len(commit_days)) if commit_days else None
        daily_commits = self._daily_commit_counts(snapshot)
        return WorkHistory(
            issue_count=len(issues),
            open_issue_count=len(open_issues),
            open_pull_request_count=len(open_prs),
            merged_pull_request_count=len(merged),
            commit_count=len(snapshot.commits),
            open_issue_units=round(open_issue_units, 6),
            open_pull_request_units=round(open_pr_units, 6),
            remaining_units=round(open_issue_units + open_pr_units, 6),
            completed_units=round(sum(self._weight(p.labels) for p in merged), 6),
            active_commit_days=len(commit_days),
            active_merge_days=len(merge_rates),
            mean_units_per_merge_day=self._mean(merge_rates),
            median_units_per_merge_day=self._median(merge_rates),
            mean_commits_per_active_day=commit_rates,
            median_commits_per_active_day=self._median(daily_commits),
        )

    def _weight(self, labels: Sequence[str]) -> float:
        normalized = {label.casefold().replace("size/", "") for label in labels}
        for label, value in self._weights:
            if label.replace("size/", "") in normalized:
                return value
        return next(
            (value for label, value in self._weights if label.replace("size/", "") == "s"),
            self._weights[0][1],
        )

    @staticmethod
    def _day(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date().isoformat()
        except ValueError:
            return None

    @staticmethod
    def _mean(values: Sequence[float]) -> float | None:
        return None if not values else sum(values) / len(values)

    @staticmethod
    def _median(values: Sequence[float]) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2

    @classmethod
    def _daily_commit_counts(cls, snapshot: DeliverySourceSnapshotInterface) -> tuple[float, ...]:
        counts: dict[str, int] = {}
        for commit in snapshot.commits:
            day = cls._day(commit.committed_at)
            if day is not None:
                counts[day] = counts.get(day, 0) + 1
        return tuple(float(value) for value in counts.values())


@dataclass(frozen=True, slots=True)
class BillingUsage(BillingUsageInterface):
    """Cumulative conductor usage; ``None`` means no source measured that dimension."""

    elapsed_seconds: float | None = None
    dollars: float | None = None
    turn_completed_events: int | None = None
    budget_turns: int | None = None
    ledger_events: int | None = None
    phase_transition_events: int | None = None
    capacity_rejections: int | None = None
    handoffs: int | None = None
    tool_invocations: int | None = None
    file_edits: int | None = None
    artifacts_produced: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in BILLING_USAGE_FIELDS}


@dataclass(frozen=True, slots=True)
class BillingForecast(BillingForecastInterface):
    actual: BillingUsage
    planned_low: BillingUsage
    planned_high: BillingUsage
    completion_low: BillingUsage
    completion_high: BillingUsage
    unknowns: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "actual": self.actual.as_dict(),
            "planned_low": self.planned_low.as_dict(),
            "planned_high": self.planned_high.as_dict(),
            "completion_low": self.completion_low.as_dict(),
            "completion_high": self.completion_high.as_dict(),
            "unknowns": list(self.unknowns),
        }


@dataclass(frozen=True, slots=True)
class PhiConfig(PhiConfigInterface):
    """Configurable dilation constants; the paper leaves ``phi`` empirical."""

    floor: float = 0.1
    epsilon: float = 0.01
    exponent: float = 1.0
    unknown_factor: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.floor < 1.0:
            raise ValueError("phi floor must be at least 0 and below 1")
        if self.epsilon <= 0 or not math.isfinite(self.epsilon):
            raise ValueError("phi epsilon must be positive and finite")
        if self.exponent <= 0 or not math.isfinite(self.exponent):
            raise ValueError("phi exponent must be positive and finite")
        if self.unknown_factor < 1.0 or not math.isfinite(self.unknown_factor):
            raise ValueError("unknown phi factor must be finite and at least 1")


@dataclass(frozen=True, slots=True)
class DeliveryTrackRecord(DeliveryTrackRecordInterface):
    time: TrackRecord
    dollars: TrackRecord
    dimension_records: tuple[tuple[str, TrackRecord], ...] = ()

    @property
    def dimensions(self) -> Mapping[str, TrackRecord]:
        return dict(self.dimension_records)

    @staticmethod
    def _record_dict(record: TrackRecord) -> dict[str, object]:
        return {
            "graded": record.graded,
            "ungraded": record.ungraded,
            "mean_error": record.mean_error,
            "mean_abs_error": record.mean_abs_error,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "time": self._record_dict(self.time),
            "dollars": self._record_dict(self.dollars),
            "dimensions": {
                name: self._record_dict(record) for name, record in self.dimension_records
            },
        }


@dataclass(frozen=True, slots=True)
class DeliveryForecast(DeliveryForecastInterface):
    recorded_at: str
    source_fingerprint: str
    history: WorkHistory
    actual_usage: BillingUsage
    billing: BillingForecast
    state: StateVector
    phi_product: float
    time_days_low: float | None
    time_days_high: float | None
    first_repair: tuple[str, ...]
    track_record: DeliveryTrackRecord
    phi: tuple[tuple[str, float | None, float], ...] = ()
    assumptions: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "vibey-delivery-forecast/v1",
            "recorded_at": self.recorded_at,
            "source_fingerprint": self.source_fingerprint,
            "history": self.history.as_dict(),
            "time": {
                "days_low": self.time_days_low,
                "days_high": self.time_days_high,
                "phi_product": self.phi_product,
                "first_repair": list(self.first_repair),
            },
            "billing": self.billing.as_dict(),
            "materials": [
                {
                    "coordinate": coordinate.name,
                    "value": coordinate.value,
                    "distance": coordinate.distance,
                    "source": coordinate.source,
                    "phi": {name: dilation for name, _value, dilation in self.phi}.get(
                        coordinate.name
                    ),
                }
                for coordinate in self.state.coordinates
            ],
            "track_record": self.track_record.as_dict(),
            "assumptions": list(self.assumptions),
            "problems": list(self.problems),
        }

    def event_payload(self) -> Mapping[str, object]:
        """The safe, replayable payload for ``DeliveryEstimateRecorded``."""
        return self.as_dict()

    def lines(self) -> list[str]:
        headline = "vibey-gh forecast:"
        remaining = f"{self.history.remaining_units:g} work unit(s) remain"
        if self.time_days_low is None or self.time_days_high is None:
            time_line = "time: unknown — no measured throughput band"
        else:
            time_line = (
                f"time: {self.time_days_low:.2f}–{self.time_days_high:.2f} active day(s)"
                f" after φ={self.phi_product:.3g}"
            )
        actual = self._usage_line(self.billing.actual)
        planned = self._usage_line(self.billing.planned_low, high=self.billing.planned_high)
        track = self.track_record.as_dict()
        dimension_track = ", ".join(
            f"{name}={record.graded} graded/{record.ungraded} ungraded"
            for name, record in self.track_record.dimensions.items()
        )
        out = [
            f"{headline} {remaining}; {self.history.completed_units:g} completed",
            f"{headline} {time_line}",
            f"{headline} billing actual: {actual}",
            f"{headline} billing planned: {planned}",
            f"{headline} track record: time={track['time']}; dollars={track['dollars']}",
            f"{headline} billing track records: {dimension_track or 'none yet'}",
            f"{headline} materials measured: {self.state.measured}/18",
        ]
        if self.first_repair:
            out.append(f"{headline} first repair candidates: {', '.join(self.first_repair)}")
        else:
            out.append(f"{headline} first repair: unknown — no measured material shortfall")
        if self.billing.unknowns:
            out.append(f"{headline} billing unknowns: {', '.join(self.billing.unknowns)}")
        for problem in self.problems:
            out.append(f"{headline} source problem: {problem}")
        return out

    @staticmethod
    def _usage_line(
        low: BillingUsageInterface, *, high: BillingUsageInterface | None = None
    ) -> str:
        high = low if high is None else high
        parts: list[str] = []
        for field in BILLING_USAGE_FIELDS:
            first = getattr(low, field)
            last = getattr(high, field)
            if first is None:
                shown = "unknown"
            elif first == last:
                shown = str(first)
            else:
                shown = f"{first}–{last}"
            parts.append(f"{field}={shown}")
        return ", ".join(parts)


class DeliveryEstimator(DeliveryEstimatorInterface):
    """Calculates a forecast and grades prior per-unit predictions."""

    def __init__(
        self,
        *,
        phi: PhiConfigInterface | None = None,
        estimator: GradedEstimator | None = None,
    ) -> None:
        self._phi = phi or PhiConfig()
        self._estimator = estimator or GradedEstimator()

    def calculate(
        self,
        history: WorkHistoryInterface,
        actual: BillingUsageInterface,
        *,
        state: StateVector,
        recorded_at: str,
        source_fingerprint: str,
        prior_records: Sequence[Mapping[str, object]] = (),
        assumptions: Sequence[str] = (),
        problems: Sequence[str] = (),
    ) -> DeliveryForecast:
        low_rate, high_rate = self._rates(history)
        phi_entries = tuple(self._coordinate_phi(coordinate) for coordinate in state.coordinates)
        phi_product = math.prod(entry[2] for entry in phi_entries)
        base_low, base_high = self._base_days(history.remaining_units, low_rate, high_rate)
        time_low = None if base_low is None else base_low * phi_product
        time_high = None if base_high is None else base_high * phi_product
        planned_low = self._planned_usage(
            actual,
            history,
            time_low,
            time_is_days=True,
        )
        planned_high = self._planned_usage(
            actual,
            history,
            time_high,
            time_is_days=True,
        )
        if time_low is None:
            fallback_low = self._per_unit_seconds(actual, history)
            planned_low = self._replace_elapsed(planned_low, fallback_low)
        if time_high is None:
            fallback_high = self._per_unit_seconds(actual, history)
            planned_high = self._replace_elapsed(planned_high, fallback_high)
        completion_low = self._sum_usage(actual, planned_low)
        completion_high = self._sum_usage(actual, planned_high)
        unknowns = self._unknowns(planned_low, history.remaining_units)
        if time_low is None:
            unknowns.append("elapsed_seconds: no historical throughput band")
        track = self._track_record(prior_records, history, actual)
        derived_assumptions = [
            "remaining work is open non-PR issues plus open PRs, weighted by size labels",
            "completed work is merged PRs, weighted by the same size labels",
            "throughput band is the observed mean/median merged work-unit rate per active merge day",
            (
                f"phi_i uses ((1-floor) / max(value-floor, epsilon))^exponent for measured"
                f" coordinates; floor={self._phi.floor:g}, epsilon={self._phi.epsilon:g},"
                f" exponent={self._phi.exponent:g}"
            ),
            f"unknown material coordinates use phi={self._phi.unknown_factor:g}",
            "planned billing dimensions scale observed cumulative usage by remaining/completed work",
        ]
        all_assumptions = tuple(dict.fromkeys((*assumptions, *derived_assumptions)))
        return DeliveryForecast(
            recorded_at=recorded_at,
            source_fingerprint=source_fingerprint,
            history=_as_history(history),
            actual_usage=_as_usage(actual),
            billing=BillingForecast(
                actual=_as_usage(actual),
                planned_low=planned_low,
                planned_high=planned_high,
                completion_low=completion_low,
                completion_high=completion_high,
                unknowns=tuple(dict.fromkeys(unknowns)),
            ),
            state=state,
            phi_product=round(phi_product, 8),
            time_days_low=_rounded(time_low),
            time_days_high=_rounded(time_high),
            first_repair=self._first_repairs(phi_entries),
            track_record=track,
            assumptions=all_assumptions,
            problems=tuple(problems),
            phi=phi_entries,
        )

    def _coordinate_phi(self, coordinate: Coordinate) -> tuple[str, float | None, float]:
        value = coordinate.value
        if value is None:
            return coordinate.name, None, self._phi.unknown_factor
        denominator = max(value - self._phi.floor, self._phi.epsilon)
        numerator = max(1.0 - self._phi.floor, self._phi.epsilon)
        dilation = max(1.0, (numerator / denominator) ** self._phi.exponent)
        return coordinate.name, value, round(dilation, 8)

    @staticmethod
    def _rates(history: WorkHistoryInterface) -> tuple[float | None, float | None]:
        rates = tuple(
            rate
            for rate in (history.mean_units_per_merge_day, history.median_units_per_merge_day)
            if rate is not None and rate > 0
        )
        return (None, None) if not rates else (min(rates), max(rates))

    @staticmethod
    def _base_days(
        remaining: float, low_rate: float | None, high_rate: float | None
    ) -> tuple[float | None, float | None]:
        if remaining <= 0:
            return 0.0, 0.0
        if low_rate is None or high_rate is None:
            return None, None
        return remaining / high_rate, remaining / low_rate

    def _planned_usage(
        self,
        actual: BillingUsageInterface,
        history: WorkHistoryInterface,
        time_days: float | None,
        *,
        time_is_days: bool,
    ) -> BillingUsage:
        values: dict[str, float | int | None] = {}
        for field in BILLING_USAGE_FIELDS:
            raw = getattr(actual, field)
            if history.remaining_units <= 0:
                value: float | int | None = 0
            elif field == "elapsed_seconds" and time_days is not None and time_is_days:
                value = time_days * 86_400
            elif raw is None or history.completed_units <= 0:
                value = None
            else:
                value = raw / history.completed_units * history.remaining_units
                if field not in {"elapsed_seconds", "dollars"}:
                    value = round(value)
            values[field] = value
        return _usage_from_values(values)

    @staticmethod
    def _replace_elapsed(usage: BillingUsage, seconds_per_unit: float | None) -> BillingUsage:
        if usage.elapsed_seconds is not None or seconds_per_unit is None:
            return usage
        return replace(usage, elapsed_seconds=seconds_per_unit)

    @staticmethod
    def _per_unit_seconds(
        actual: BillingUsageInterface, history: WorkHistoryInterface
    ) -> float | None:
        if actual.elapsed_seconds is None or history.completed_units <= 0:
            return None
        return actual.elapsed_seconds / history.completed_units * history.remaining_units

    @staticmethod
    def _sum_usage(first: BillingUsageInterface, second: BillingUsageInterface) -> BillingUsage:
        values: dict[str, float | int | None] = {}
        for field in BILLING_USAGE_FIELDS:
            left, right = getattr(first, field), getattr(second, field)
            if left is None or right is None:
                values[field] = None
            else:
                total = left + right
                values[field] = round(total, 8) if isinstance(total, float) else int(total)
        return _usage_from_values(values)

    @staticmethod
    def _unknowns(usage: BillingUsageInterface, remaining: float) -> list[str]:
        if remaining <= 0:
            return []
        return [field for field in BILLING_USAGE_FIELDS if getattr(usage, field) is None]

    @staticmethod
    def _first_repairs(phi: Sequence[tuple[str, float | None, float]]) -> tuple[str, ...]:
        measured = [entry for entry in phi if entry[1] is not None and entry[2] > 1.0]
        return tuple(entry[0] for entry in sorted(measured, key=lambda item: (-item[2], item[0])))

    def _track_record(
        self,
        prior_records: Sequence[Mapping[str, object]],
        history: WorkHistoryInterface,
        actual: BillingUsageInterface,
    ) -> DeliveryTrackRecord:
        grades: dict[str, list[Grade]] = {field: [] for field in BILLING_USAGE_FIELDS}
        for record in prior_records:
            previous = self._prior_values(record)
            if previous is None:
                for field_grades in grades.values():
                    field_grades.append(Grade(None, 0.0, "none", 0))
                continue
            previous_units, previous_completed, planned, previous_actual = previous
            completed_since = history.completed_units - previous_completed
            if completed_since <= 0:
                for field_grades in grades.values():
                    field_grades.append(Grade(None, 0.0, "none", 0))
                continue
            for field, field_grades in grades.items():
                previous_plan = _number(planned.get(field))
                delta = self._delta(
                    _number(getattr(actual, field)), _number(previous_actual.get(field))
                )
                if previous_plan is None or previous_units <= 0 or delta is None:
                    field_grades.append(Grade(None, 0.0, "none", 0))
                    continue
                prediction = Prediction(
                    previous_plan / previous_units,
                    0.0,
                    "ledger-per-unit",
                    1,
                    "prior forecast",
                )
                field_grades.append(self._estimator.grade(prediction, delta / completed_since))
        records = {
            field: self._estimator.track_record(field_grades)
            for field, field_grades in grades.items()
        }
        return DeliveryTrackRecord(
            time=records["elapsed_seconds"],
            dollars=records["dollars"],
            dimension_records=tuple(records.items()),
        )

    @staticmethod
    def _prior_values(
        record: Mapping[str, object],
    ) -> tuple[float, float, Mapping[str, object], Mapping[str, object]] | None:
        history = record.get("history")
        billing = record.get("billing")
        if not isinstance(history, Mapping) or not isinstance(billing, Mapping):
            return None
        units = history.get("work_units")
        if not isinstance(units, Mapping):
            return None
        previous_units = _number(units.get("remaining"))
        previous_completed = _number(units.get("completed"))
        if previous_units is None or previous_completed is None:
            return None
        planned = billing.get("planned_low")
        actual = billing.get("actual")
        if not isinstance(planned, Mapping) or not isinstance(actual, Mapping):
            return None
        return previous_units, previous_completed, planned, actual

    @staticmethod
    def _delta(current: float | None, previous: float | None) -> float | None:
        if current is None or previous is None:
            return None
        return max(0.0, current - previous)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 8)


def _as_history(history: WorkHistoryInterface) -> WorkHistory:
    return (
        history
        if isinstance(history, WorkHistory)
        else WorkHistory(
            **{
                field: getattr(history, field)
                for field in (
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
            }
        )
    )


def _as_usage(usage: BillingUsageInterface) -> BillingUsage:
    return (
        usage
        if isinstance(usage, BillingUsage)
        else _usage_from_values({field: getattr(usage, field) for field in BILLING_USAGE_FIELDS})
    )


def _usage_from_values(values: Mapping[str, object]) -> BillingUsage:
    return BillingUsage(
        elapsed_seconds=_optional_float(values.get("elapsed_seconds")),
        dollars=_optional_float(values.get("dollars")),
        turn_completed_events=_optional_int(values.get("turn_completed_events")),
        budget_turns=_optional_int(values.get("budget_turns")),
        ledger_events=_optional_int(values.get("ledger_events")),
        phase_transition_events=_optional_int(values.get("phase_transition_events")),
        capacity_rejections=_optional_int(values.get("capacity_rejections")),
        handoffs=_optional_int(values.get("handoffs")),
        tool_invocations=_optional_int(values.get("tool_invocations")),
        file_edits=_optional_int(values.get("file_edits")),
        artifacts_produced=_optional_int(values.get("artifacts_produced")),
    )


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None
