# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for the project notification, telemetry and queue configuration values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.queue_reap import BrokerPolicy, ReapThresholds


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
class QueueConfigInterface(Protocol):
    """`[queue]`."""

    @property
    def priority(self) -> QueuePriorityConfigInterface: ...

    @property
    def reap(self) -> QueueReapConfigInterface: ...
