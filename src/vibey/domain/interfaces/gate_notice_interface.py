# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind gate notices.

Mirrors `vibey/domain/gate_notice.py` (ADR-0016). Interfaces declare; they never consume.
The domain types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping

    from vibey.domain.gate_notice import NoticeReason
    from vibey.domain.interfaces.config_interface import NotificationsConfigInterface


@runtime_checkable
class ReminderScheduleInterface(Protocol):
    """When a waiting gate is reminded about."""

    @property
    def after_seconds(self) -> int: ...

    @property
    def every_seconds(self) -> int: ...

    @property
    def max_reminders(self) -> int: ...

    def due(self, *, waited_seconds: float, recorded: frozenset[int], silent: bool) -> int | None:
        """The notice number to send now -- 0 when the raise notice is not on record --
        or None when nothing is due."""
        ...


@runtime_checkable
class NoticeChannelsInterface(Protocol):
    """Reads a project's configured channels against what a sink reported."""

    def silence(self, config: NotificationsConfigInterface) -> NoticeReason | None: ...

    def undelivered(
        self, result: Mapping[str, object], config: NotificationsConfigInterface
    ) -> str | None: ...
