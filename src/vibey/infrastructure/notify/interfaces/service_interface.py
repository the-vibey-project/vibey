# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the composite notification service (ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from vibey.application.interfaces.observability import NotificationSink

if TYPE_CHECKING:
    from vibey.infrastructure.notify.events import NotificationEvent


@runtime_checkable
class NotificationServiceInterface(NotificationSink, Protocol):
    """Coordinates operator notifications across desktop, webhooks, and sovereign surfaces."""

    def for_project_config(
        self, config: Mapping[str, object] | None
    ) -> NotificationServiceInterface:
        """Return the channel policy for one project's stored configuration."""
        ...

    def has_channels(self) -> bool:
        """Whether any notification channel is configured and enabled."""
        ...

    async def dispatch(self, event: NotificationEvent) -> dict[str, Any]:
        """Deliver the notification to all active channels."""
        ...
