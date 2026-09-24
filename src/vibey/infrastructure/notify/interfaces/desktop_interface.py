# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the desktop notification sender.

Mirrors `vibey/infrastructure/notify/desktop.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # the event record lives beside its sender
    from vibey.infrastructure.notify.events import NotificationEvent


@runtime_checkable
class DesktopNotifierInterface(Protocol):
    """Shows one notification on the operator's desktop."""

    async def notify(self, event: "NotificationEvent") -> bool:
        """Whether the platform's notifier accepted it. The event's text is passed as
        data -- an argument -- and never becomes part of a script."""
        ...
