# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices: whether a person was told a gate is waiting, as evidence.

A gate parks a job until a person answers it (ADR-0009), which only works if a person
knows. Every notice about a gate -- notice 0 when it is raised, reminder 1, 2, ... while
it waits -- ends in exactly one ledger record: `GateNotified` when at least one channel
took it, `GateNoticeUndeliverable` with the reason when none could. Nothing is assumed
delivered, and a gate nobody could be told about is said once, loudly, not never.

Pure: which notice is due, why none can be sent, and whether a channel's result was a
delivery. Sending and recording are the application's.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Final
from uuid import UUID

from vibey.domain.interfaces.gate_notice_interface import NoticeChannelsInterface
from vibey.domain.ledger import EventKind

if TYPE_CHECKING:
    from vibey.domain.interfaces.config_interface import NotificationsConfigInterface

RAISED_NOTICE: Final = 0
"""The notice sent when a gate is raised. Reminders count up from 1."""

DEFAULT_REMIND_AFTER_SECONDS: Final = 86_400
"""A day: how long a gate waits before its first reminder, unless configured."""

DEFAULT_REMIND_EVERY_SECONDS: Final = 86_400
"""A day between reminders, unless configured."""

DEFAULT_MAX_REMINDERS: Final = 7
"""A week of daily reminders at the defaults; then the gate is left to `vibey gates`."""

DEFAULT_SWEEP_INTERVAL_SECONDS: Final = 300
"""How often an idle worker looks for due reminders: well inside any sensible cadence."""


class NoticeReason(StrEnum):
    """Why a notice reached nobody."""

    DISABLED = "disabled"
    """`[notifications] enabled` is false -- the default."""
    NO_CHANNEL = "no_channel"
    """Enabled, but with desktop alerts off and no webhook: there is nowhere to send it."""
    CONFIG_INVALID = "config_invalid"
    """The project's `[notifications]` table does not parse, so no channel can be trusted."""
    UNWIRED = "unwired"
    """This process was composed without a notification sink."""
    FAILED = "failed"
    """A channel was tried and did not deliver."""


SILENT_REASONS: Final = frozenset(
    {
        NoticeReason.DISABLED,
        NoticeReason.NO_CHANNEL,
        NoticeReason.CONFIG_INVALID,
        NoticeReason.UNWIRED,
    }
)
"""Reasons no notice about the project's gates can reach anyone until something changes.
Said once per gate, at its raise notice; its reminders are then not attempted."""


@dataclass(frozen=True, slots=True)
class GateNotice:
    """One notice about one gate, and what became of it."""

    project_id: UUID
    gate_id: UUID
    gate_kind: str
    job_id: UUID | None
    notice: int
    """0 for the raise, 1.. for each reminder: with `gate_id`, the notice's identity."""
    reason: NoticeReason | None = None
    """None when delivered; else why it reached nobody."""
    detail: str | None = None
    channels: Mapping[str, object] = field(default_factory=dict)
    """What each channel reported, as the sink returned it."""

    @property
    def delivered(self) -> bool:
        return self.reason is None

    @property
    def event_kind(self) -> EventKind:
        return EventKind.GATE_NOTIFIED if self.delivered else EventKind.GATE_NOTICE_UNDELIVERABLE

    def payload(self) -> dict[str, object]:
        body: dict[str, object] = {
            "gate_id": str(self.gate_id),
            "gate_kind": self.gate_kind,
            "job_id": str(self.job_id) if self.job_id is not None else None,
            "notice": self.notice,
        }
        if self.delivered:
            body["channels"] = dict(self.channels)
        else:
            body["reason"] = str(self.reason)
            body["detail"] = self.detail
        return body


@dataclass(frozen=True, slots=True)
class ReminderSchedule:
    """When a waiting gate is reminded about: first after `after_seconds`, then every
    `every_seconds`, at most `max_reminders` times (0: never)."""

    after_seconds: int = DEFAULT_REMIND_AFTER_SECONDS
    every_seconds: int = DEFAULT_REMIND_EVERY_SECONDS
    max_reminders: int = DEFAULT_MAX_REMINDERS

    def due(self, *, waited_seconds: float, recorded: frozenset[int], silent: bool) -> int | None:
        """The notice to send now, or None.

        A gate with no raise notice on record gets one first -- one raised before this
        release, or by a process that could not record it. Then the latest reminder the
        clock has reached, if it is past every one recorded: a sweep that was down for a
        week sends the one reminder now due, not the seven it missed. `silent` projects
        get no reminders; their raise notice already said nobody would hear them.
        """
        if RAISED_NOTICE not in recorded:
            return RAISED_NOTICE
        if silent or self.max_reminders == 0 or waited_seconds < self.after_seconds:
            return None
        reached = int((waited_seconds - self.after_seconds) // self.every_seconds) + 1
        number = min(self.max_reminders, reached)
        return number if number > max(recorded) else None


class NoticeChannels:
    """Reads a project's configured channels against what a sink reported. Stateless."""

    def silence(self, config: "NotificationsConfigInterface") -> NoticeReason | None:
        """Why no notice can reach anyone under `config`, or None when a channel exists."""
        if not config.enabled:
            return NoticeReason.DISABLED
        if not config.desktop and not config.webhooks:
            return NoticeReason.NO_CHANNEL
        return None

    def undelivered(
        self, result: Mapping[str, object], config: "NotificationsConfigInterface"
    ) -> str | None:
        """Why an enabled project's notice was not delivered, or None when every
        configured channel reported delivery. A result is read, never trusted to be
        whole: a missing or short webhook list is a failure, not a success (12.e)."""
        if result.get("error"):
            return str(result["error"])
        if result.get("enabled") is False:
            return "notification service reported disabled"
        if config.desktop and result.get("desktop") is not True:
            return "desktop delivery returned false"
        if not config.webhooks:
            return None
        deliveries = result.get("webhooks")
        if not isinstance(deliveries, Sequence) or isinstance(deliveries, str | bytes):
            return "webhook delivery results were missing"
        if len(deliveries) != len(config.webhooks):
            return "webhook delivery results did not match configured destinations"
        if any(delivery is not True for delivery in deliveries):
            return "webhook delivery returned false"
        return None


NOTICE_CHANNELS: Final[NoticeChannelsInterface] = NoticeChannels()
