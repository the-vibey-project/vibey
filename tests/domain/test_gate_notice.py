# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices as evidence (domain/gate_notice.py): which notice is due, why none can be
sent, and whether what a sink reported was a delivery."""

from uuid import uuid4

import pytest

from vibey.domain.config import NotificationsConfig, NotificationWebhookConfig
from vibey.domain.gate_notice import (
    NOTICE_CHANNELS,
    RAISED_NOTICE,
    SILENT_REASONS,
    GateNotice,
    NoticeReason,
    ReminderSchedule,
)
from vibey.domain.interfaces.gate_notice_interface import (
    NoticeChannelsInterface,
    ReminderScheduleInterface,
)
from vibey.domain.ledger import EventKind

DAY = 86_400


def test_the_shared_instances_satisfy_their_declared_seams() -> None:
    assert isinstance(NOTICE_CHANNELS, NoticeChannelsInterface)
    assert isinstance(ReminderSchedule(), ReminderScheduleInterface)


def test_every_reason_but_a_failed_delivery_is_silence() -> None:
    assert frozenset(NoticeReason) - SILENT_REASONS == {NoticeReason.FAILED}


def test_a_delivered_notice_records_its_channels() -> None:
    gate_id, job_id = uuid4(), uuid4()
    notice = GateNotice(
        project_id=uuid4(),
        gate_id=gate_id,
        gate_kind="approval",
        job_id=job_id,
        notice=RAISED_NOTICE,
        channels={"desktop": True, "webhooks": []},
    )
    assert notice.delivered
    assert notice.event_kind is EventKind.GATE_NOTIFIED
    assert notice.payload() == {
        "gate_id": str(gate_id),
        "gate_kind": "approval",
        "job_id": str(job_id),
        "notice": 0,
        "channels": {"desktop": True, "webhooks": []},
    }


def test_an_undeliverable_notice_records_why() -> None:
    gate_id = uuid4()
    notice = GateNotice(
        project_id=uuid4(),
        gate_id=gate_id,
        gate_kind="delivery_exhausted",
        job_id=None,
        notice=2,
        reason=NoticeReason.DISABLED,
        detail="nobody will be told",
    )
    assert not notice.delivered
    assert notice.event_kind is EventKind.GATE_NOTICE_UNDELIVERABLE
    assert notice.payload() == {
        "gate_id": str(gate_id),
        "gate_kind": "delivery_exhausted",
        "job_id": None,
        "notice": 2,
        "reason": "disabled",
        "detail": "nobody will be told",
    }


SCHEDULE = ReminderSchedule(after_seconds=DAY, every_seconds=DAY, max_reminders=3)


@pytest.mark.parametrize(
    ("waited", "recorded", "silent", "due"),
    [
        # No raise notice on record: that first, whatever else holds.
        (0, frozenset(), False, RAISED_NOTICE),
        (10 * DAY, frozenset(), True, RAISED_NOTICE),
        (10 * DAY, frozenset({2}), False, RAISED_NOTICE),
        # Not yet stale.
        (DAY - 1, frozenset({0}), False, None),
        # The first reminder, then each cadence step.
        (DAY, frozenset({0}), False, 1),
        (2 * DAY - 1, frozenset({0, 1}), False, None),
        (2 * DAY, frozenset({0, 1}), False, 2),
        # A sweep that was down sends the one reminder now due, not the ones it missed.
        (3 * DAY + 5, frozenset({0}), False, 3),
        # Bounded: never past `max_reminders`.
        (30 * DAY, frozenset({0, 3}), False, None),
        (30 * DAY, frozenset({0, 1}), False, 3),
        # A silent project is said once, at the raise notice, and not reminded about.
        (5 * DAY, frozenset({0}), True, None),
    ],
)
def test_the_due_notice(
    waited: float, recorded: frozenset[int], silent: bool, due: int | None
) -> None:
    assert SCHEDULE.due(waited_seconds=waited, recorded=recorded, silent=silent) == due


def test_no_reminders_when_none_are_allowed() -> None:
    never = ReminderSchedule(max_reminders=0)
    assert never.due(waited_seconds=30 * DAY, recorded=frozenset({0}), silent=False) is None


def _config(**values: object) -> NotificationsConfig:
    return NotificationsConfig(**values)  # type: ignore[arg-type]


HOOK = NotificationWebhookConfig(url="https://example.test/hook")


@pytest.mark.parametrize(
    ("config", "reason"),
    [
        (_config(), NoticeReason.DISABLED),
        (_config(enabled=True, desktop=False), NoticeReason.NO_CHANNEL),
        (_config(enabled=True), None),
        (_config(enabled=True, desktop=False, webhooks=(HOOK,)), None),
    ],
)
def test_silence(config: NotificationsConfig, reason: NoticeReason | None) -> None:
    assert NOTICE_CHANNELS.silence(config) == reason


def test_what_a_sink_reported_is_read_against_the_configured_channels() -> None:
    enabled = _config(enabled=True)
    with_webhook = _config(enabled=True, desktop=False, webhooks=(HOOK,))
    undelivered = NOTICE_CHANNELS.undelivered

    assert undelivered({"error": "boom"}, enabled) == "boom"
    assert undelivered({"enabled": False}, enabled) == "notification service reported disabled"
    assert undelivered({"enabled": True}, enabled) == "desktop delivery returned false"
    assert undelivered({"desktop": True}, enabled) is None
    assert undelivered({"enabled": True, "webhooks": "bad"}, with_webhook) == (
        "webhook delivery results were missing"
    )
    assert undelivered({"enabled": True, "webhooks": []}, with_webhook) == (
        "webhook delivery results did not match configured destinations"
    )
    assert undelivered({"enabled": True, "webhooks": [False]}, with_webhook) == (
        "webhook delivery returned false"
    )
    assert undelivered({"enabled": True, "webhooks": [True]}, with_webhook) is None
