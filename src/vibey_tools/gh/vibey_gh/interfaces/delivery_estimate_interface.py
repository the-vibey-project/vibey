# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ports for the continuous delivery-calculus forecast.

The implementation lives in :mod:`vibey_gh.delivery_estimate`.  This module is
deliberately a declaration-only seam: a caller can depend on the shapes of the
history, billing and forecast records without importing the calculator that
implements them (ADR-0016).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.estimation import TrackRecord
    from vibey_gh.feasibility import StateVector


@runtime_checkable
class IssueObservationInterface(Protocol):
    @property
    def number(self) -> int: ...

    @property
    def state(self) -> str: ...

    @property
    def is_pull_request(self) -> bool: ...

    @property
    def labels(self) -> tuple[str, ...]: ...


@runtime_checkable
class PullRequestObservationInterface(Protocol):
    @property
    def number(self) -> int: ...

    @property
    def state(self) -> str: ...

    @property
    def merged_at(self) -> str | None: ...

    @property
    def labels(self) -> tuple[str, ...]: ...


@runtime_checkable
class CommitObservationInterface(Protocol):
    @property
    def sha(self) -> str: ...

    @property
    def committed_at(self) -> str: ...


@runtime_checkable
class DeliverySourceSnapshotInterface(Protocol):
    @property
    def issues(self) -> tuple[IssueObservationInterface, ...]: ...

    @property
    def pull_requests(self) -> tuple[PullRequestObservationInterface, ...]: ...

    @property
    def commits(self) -> tuple[CommitObservationInterface, ...]: ...

    @property
    def source_revision(self) -> str: ...

    @property
    def fingerprint(self) -> str: ...

    @property
    def problems(self) -> tuple[str, ...]: ...


@runtime_checkable
class WorkHistoryInterface(Protocol):
    @property
    def issue_count(self) -> int: ...

    @property
    def open_issue_count(self) -> int: ...

    @property
    def open_pull_request_count(self) -> int: ...

    @property
    def merged_pull_request_count(self) -> int: ...

    @property
    def commit_count(self) -> int: ...

    @property
    def open_issue_units(self) -> float: ...

    @property
    def open_pull_request_units(self) -> float: ...

    @property
    def remaining_units(self) -> float: ...

    @property
    def completed_units(self) -> float: ...

    @property
    def active_commit_days(self) -> int: ...

    @property
    def active_merge_days(self) -> int: ...

    @property
    def mean_units_per_merge_day(self) -> float | None: ...

    @property
    def median_units_per_merge_day(self) -> float | None: ...

    @property
    def mean_commits_per_active_day(self) -> float | None: ...

    @property
    def median_commits_per_active_day(self) -> float | None: ...

    def as_dict(self) -> dict[str, object]: ...


@runtime_checkable
class BillingUsageInterface(Protocol):
    """Cumulative usage, including every dimension the billing brake can see."""

    @property
    def elapsed_seconds(self) -> float | None: ...

    @property
    def dollars(self) -> float | None: ...

    @property
    def turn_completed_events(self) -> int | None: ...

    @property
    def budget_turns(self) -> int | None: ...

    @property
    def ledger_events(self) -> int | None: ...

    @property
    def phase_transition_events(self) -> int | None: ...

    @property
    def capacity_rejections(self) -> int | None: ...

    @property
    def handoffs(self) -> int | None: ...

    @property
    def tool_invocations(self) -> int | None: ...

    @property
    def file_edits(self) -> int | None: ...

    @property
    def artifacts_produced(self) -> int | None: ...

    def as_dict(self) -> dict[str, object]: ...


@runtime_checkable
class BillingForecastInterface(Protocol):
    @property
    def actual(self) -> BillingUsageInterface: ...

    @property
    def planned_low(self) -> BillingUsageInterface: ...

    @property
    def planned_high(self) -> BillingUsageInterface: ...

    @property
    def completion_low(self) -> BillingUsageInterface: ...

    @property
    def completion_high(self) -> BillingUsageInterface: ...

    @property
    def unknowns(self) -> tuple[str, ...]: ...

    def as_dict(self) -> dict[str, object]: ...


@runtime_checkable
class BillingLedgerSnapshotInterface(Protocol):
    @property
    def usage(self) -> BillingUsageInterface: ...

    @property
    def problems(self) -> tuple[str, ...]: ...


@runtime_checkable
class PhiConfigInterface(Protocol):
    @property
    def floor(self) -> float: ...

    @property
    def epsilon(self) -> float: ...

    @property
    def exponent(self) -> float: ...

    @property
    def unknown_factor(self) -> float: ...


@runtime_checkable
class DeliveryTrackRecordInterface(Protocol):
    @property
    def time(self) -> TrackRecord: ...

    @property
    def dollars(self) -> TrackRecord: ...

    @property
    def dimensions(self) -> Mapping[str, TrackRecord]: ...

    def as_dict(self) -> dict[str, object]: ...


@runtime_checkable
class DeliveryForecastInterface(Protocol):
    @property
    def recorded_at(self) -> str: ...

    @property
    def source_fingerprint(self) -> str: ...

    @property
    def history(self) -> WorkHistoryInterface: ...

    @property
    def actual_usage(self) -> BillingUsageInterface: ...

    @property
    def billing(self) -> BillingForecastInterface: ...

    @property
    def state(self) -> StateVector: ...

    @property
    def phi_product(self) -> float: ...

    @property
    def phi(self) -> tuple[tuple[str, float | None, float], ...]: ...

    @property
    def time_days_low(self) -> float | None: ...

    @property
    def time_days_high(self) -> float | None: ...

    @property
    def first_repair(self) -> tuple[str, ...]: ...

    @property
    def track_record(self) -> DeliveryTrackRecordInterface: ...

    @property
    def assumptions(self) -> tuple[str, ...]: ...

    @property
    def problems(self) -> tuple[str, ...]: ...

    def as_dict(self) -> dict[str, object]: ...

    def lines(self) -> list[str]: ...

    def event_payload(self) -> Mapping[str, object]: ...


@runtime_checkable
class DeliveryHistoryCalculatorInterface(Protocol):
    def calculate(self, snapshot: DeliverySourceSnapshotInterface) -> WorkHistoryInterface: ...


@runtime_checkable
class DeliverySourceReaderInterface(Protocol):
    def read(
        self, repository: str, *, root: Path, limit: int = 1000
    ) -> DeliverySourceSnapshotInterface:
        """Read forge and local history, retaining source problems as data."""
        ...


@runtime_checkable
class DeliveryEstimatorInterface(Protocol):
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
    ) -> DeliveryForecastInterface: ...


@runtime_checkable
class DeliveryEstimateLedgerInterface(Protocol):
    def read(self, path: Path) -> tuple[Mapping[str, object], ...]: ...

    def record(self, forecast: DeliveryForecastInterface, path: Path) -> bool: ...

    def write_report(self, forecast: DeliveryForecastInterface, path: Path) -> None: ...


@runtime_checkable
class BillingLedgerReaderInterface(Protocol):
    def read(self, path: Path) -> BillingLedgerSnapshotInterface: ...
