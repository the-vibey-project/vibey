# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for the project notification, telemetry, queue and design configuration values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.gate_notice import ReminderSchedule
    from vibey.domain.queue_reap import BrokerPolicy, ReapThresholds
    from vibey.domain.research_gap import ResearchOnUnavailable


@runtime_checkable
class NotificationWebhookConfigInterface(Protocol):
    @property
    def url(self) -> str: ...

    @property
    def secret(self) -> str | None: ...


@runtime_checkable
class NotificationsConfigInterface(Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def desktop(self) -> bool: ...

    @property
    def webhooks(self) -> tuple[NotificationWebhookConfigInterface, ...]: ...

    @property
    def remind_after_seconds(self) -> int: ...

    @property
    def remind_every_seconds(self) -> int: ...

    @property
    def max_reminders(self) -> int: ...

    @property
    def sweep_interval_seconds(self) -> int: ...

    def reminders(self) -> ReminderSchedule:
        """The schedule a waiting gate is reminded on."""
        ...


@runtime_checkable
class TelemetryConfigInterface(Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def export_path(self) -> str | None: ...


@runtime_checkable
class QueuePriorityConfigInterface(Protocol):
    """`[queue.priority]` (ADR-0054)."""

    @property
    def sources(self) -> tuple[str, ...]:
        """The declared sources besides the operator, as written, in order."""
        ...


@runtime_checkable
class QueueReapConfigInterface(Protocol):
    """`[queue.reap]` (ADR-0056)."""

    @property
    def enabled(self) -> bool: ...

    @property
    def interval_seconds(self) -> int: ...

    @property
    def dead_letter_peek_limit(self) -> int: ...

    def thresholds(self) -> ReapThresholds: ...

    def broker_policy(self) -> BrokerPolicy: ...


@runtime_checkable
class QueueDefectConfigInterface(Protocol):
    """`[queue.defect]`."""

    @property
    def identical_failures(self) -> int:
        """How many consecutive identical failures make a defect; 0 is off."""
        ...


@runtime_checkable
class QueueConfigInterface(Protocol):
    """`[queue]`."""

    @property
    def priority(self) -> QueuePriorityConfigInterface: ...

    @property
    def reap(self) -> QueueReapConfigInterface: ...

    @property
    def defect(self) -> QueueDefectConfigInterface: ...


@runtime_checkable
class DesignResearchConfigInterface(Protocol):
    """`[design.research]`."""

    @property
    def on_unavailable(self) -> ResearchOnUnavailable:
        """`gate` parks for a person; `record_gap` records the topic as not researched."""
        ...


@runtime_checkable
class DesignConfigInterface(Protocol):
    """`[design]`."""

    @property
    def research(self) -> DesignResearchConfigInterface: ...
