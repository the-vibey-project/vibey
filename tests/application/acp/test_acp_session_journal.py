# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Each ACP session's log, written behind to the hub in order (SP-ACP Task 6), and the channel a
prompt turn writes through so what it shows is kept.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

import pytest
from acp.schema import SessionUpdateNotice
from acp_fakes import FakeChannel, FakeHub

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.acp_journaling_channel import AcpJournalingChannel
from vibey.application.acp.acp_session_journal import (
    FORKED,
    FULL,
    OVERFLOW,
    REFUSED,
    UNGRANTED,
    UNKEEPABLE_FOLDER,
    UNKEPT,
    UNSENT,
    AcpSessionJournal,
)
from vibey.application.acp.interfaces.acp_session_journal_interface import (
    AcpSessionJournalInterface,
)
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.protocol import ToolCallStatus
from vibey.domain.acp.session_log import (
    STORED_EVENT_BYTES,
    AcpSessionLimitReached,
    SessionEventConflict,
    SessionEventKind,
    SessionRequestRefused,
    SessionWritesThrottled,
    UnknownAcpSession,
)
from vibey.domain.acp.session_replay import SESSION_REPLAY
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.hub.app import MAX_BODY_BYTES
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError

S = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a01"
T = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a02"
MSG = SessionEventKind.USER_MESSAGE
"""What a prompt records: the first one is what makes the hub keep a new session."""
NOTICES = {"session": {"notices": {}}}


class FlakyHub(FakeHub):
    """A hub whose appends fail as scripted, by seq: `away` (unreachable), `lost` (stored, but
    the answer never came back), or an error to raise."""

    def __init__(self) -> None:
        super().__init__()
        self.script: dict[int, str | Exception] = {}
        self.in_flight = asyncio.Event()
        self.hold: asyncio.Event | None = None
        self.attempts: list[int] = []

    async def append_event(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any]
    ) -> None:
        self.attempts.append(seq)
        if self.hold is not None:
            self.in_flight.set()
            await self.hold.wait()
            self.hold = None
        scripted = self.script.pop(seq, None)
        if scripted == "away":
            raise HubGatewayError("the hub could not be reached")
        if isinstance(scripted, Exception):
            raise scripted
        await super().append_event(session_id, seq, kind, payload)
        if scripted == "lost":
            raise HubGatewayError("the hub did not answer")


def _journal(
    hub: FakeHub, *, channel: FakeChannel | None = None, pending: int = 1000
) -> AcpSessionJournal:
    return AcpSessionJournal(
        hub,
        AcpSettings(pending_events_max=pending),
        channel or FakeChannel(),
        AcpUpdateMapper(),
    )


def test_the_journal_and_the_channel_meet_their_declared_seams() -> None:
    journal = _journal(FakeHub())
    assert isinstance(journal, AcpSessionJournalInterface)
    assert isinstance(
        AcpJournalingChannel(FakeChannel(), journal, SESSION_REPLAY), ClientChannelInterface
    )


def test_an_event_the_hub_would_refuse_for_its_size_is_never_queued() -> None:
    """The cut in `AcpSessionReplay.fit` leaves room for the event's own envelope under the
    hub's body limit, whatever the payload holds."""
    envelope = json.dumps({"seq": 2**63 - 1, "kind": "tool_call_update", "payload": {}})
    assert STORED_EVENT_BYTES + len(envelope.encode()) < MAX_BODY_BYTES


async def test_flush_sends_in_order_and_resumes_after_a_failure() -> None:
    hub = FlakyHub()
    journal = _journal(hub)
    journal.open(S, "/work")
    assert [journal.record(S, MSG, {"text": str(n)}) for n in (1, 2, 3)] == [1, 2, 3]
    hub.script[2] = "away"

    await journal.flush()
    assert hub.log(S) == [(1, "user_message", {"text": "1"})]
    assert journal.persisted_seq(S) == 1

    await journal.flush()
    assert [seq for seq, _, _ in hub.log(S)] == [1, 2, 3]
    assert journal.persisted_seq(S) == 3
    assert hub.attempts == [1, 2, 2, 3]  # sent again from the failure, and only from there
    await journal.flush()  # nothing queued: nothing sent
    assert hub.attempts == [1, 2, 2, 3]


async def test_a_resend_after_a_lost_answer_writes_nothing_twice() -> None:
    hub = FlakyHub()
    journal = _journal(hub)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "once"})
    hub.script[1] = "lost"
    await journal.flush()
    assert journal.persisted_seq(S) == 0
    await journal.flush()
    assert hub.log(S) == [(1, "user_message", {"text": "once"})]
    assert journal.persisted_seq(S) == 1


async def test_a_new_sessions_create_goes_first_and_a_failed_create_holds_its_events() -> None:
    hub = FlakyHub()
    hub.session_error = HubGatewayError("away")
    journal = _journal(hub)
    journal.open(S, "/work")
    journal.open(S, "/elsewhere")  # a second open changes nothing
    journal.record(S, MSG, {"text": "x"})
    await journal.flush()
    assert hub.kept == {}
    hub.session_error = None
    await journal.flush()
    assert hub.kept[S][0] == "/work" and hub.log(S) == [(1, "user_message", {"text": "x"})]


async def test_overflow_drops_oldest_and_notices_once() -> None:
    hub = FlakyHub()
    hub.session_error = HubGatewayError("away")
    channel = FakeChannel()
    journal = _journal(hub, channel=channel, pending=3)
    journal.open(S, "/work")
    for n in range(1, 6):
        journal.record(S, MSG, {"text": str(n)})
    await journal.flush()
    await journal.flush()
    assert channel.said == [f"Session history: {OVERFLOW}"]

    hub.session_error = None
    await journal.flush()
    # The create is never the one dropped; the oldest events are.
    assert hub.kept[S][0] == "/work"
    assert [payload["text"] for _, _, payload in hub.log(S)] == ["4", "5"]
    assert channel.said == [f"Session history: {OVERFLOW}"]


async def test_the_notice_is_a_notice_when_the_client_takes_notices() -> None:
    hub = FlakyHub()
    hub.session_error = HubGatewayError("away")
    channel = FakeChannel()
    channel.client_capabilities = NOTICES
    journal = _journal(hub, channel=channel, pending=1)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "1"})
    journal.record(S, MSG, {"text": "2"})
    await journal.flush()
    (update,) = channel.updates
    assert update == {
        "sessionUpdate": "notice",
        "severity": "warning",
        "title": "Session history",
        "description": OVERFLOW,
    }
    assert_wire_exact(SessionUpdateNotice, update)


async def test_the_event_being_sent_is_never_the_one_overflow_drops() -> None:
    hub = FlakyHub()
    hub.hold = asyncio.Event()
    journal = _journal(hub, pending=2)
    journal.resume(S, 0)
    hub.kept[S] = ("/work", [])
    journal.record(S, MSG, {"text": "1"})
    flushing = asyncio.create_task(journal.flush())
    await hub.in_flight.wait()
    journal.record(S, MSG, {"text": "2"})
    journal.record(S, MSG, {"text": "3"})  # over the cap while 1 is in flight: 2 is dropped
    hub.hold.set()
    await flushing
    assert [payload["text"] for _, _, payload in hub.log(S)] == ["1", "3"]


async def test_a_conflict_stops_that_sessions_log_and_says_so_once() -> None:
    hub = FlakyHub()
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/work")
    journal.open(T, "/work")
    journal.record(S, MSG, {"text": "a"})
    journal.record(T, MSG, {"text": "b"})
    journal.record(S, MSG, {"text": "c"})
    hub.script[1] = SessionEventConflict("seq 1 is taken")
    await journal.flush()
    assert journal.recording(S) is False and journal.recording(T) is True
    assert journal.record(S, MSG, {"text": "d"}) == 0
    assert hub.log(S) == [] and hub.log(T) == [(1, "user_message", {"text": "b"})]
    assert channel.sessions == [S] and channel.said == [f"Session history: {FORKED}"]


async def test_a_session_the_hub_does_not_keep_stops_its_log() -> None:
    hub = FlakyHub()
    hub.script[1] = UnknownAcpSession("no such session")
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "a"})
    await journal.flush()
    assert channel.said == [f"Session history: {UNKEPT}"]
    assert journal.recording(S) is False


async def test_without_the_acp_sessions_grant_a_session_is_kept_in_memory_and_said_once() -> None:
    """An operator narrowed `[hub] agent_scopes`: nothing is sent, nothing fails, and the
    client is told once that the history stays in this window."""
    hub = FlakyHub()
    hub.scopes = frozenset({HubScope.VIEW, HubScope.ANSWER, HubScope.RUN})
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/work")
    journal.resume(S, 3)
    assert journal.recording(S) is False
    assert journal.record(S, MSG, {"text": "x"}) == 0
    await journal.flush()
    await journal.flush()
    assert hub.session_calls == [] and hub.attempts == []
    assert channel.sessions == [S] and channel.said == [f"Session history: {UNGRANTED}"]


async def test_a_hub_that_keeps_no_more_stops_the_log_and_says_so_once() -> None:
    hub = FlakyHub()
    hub.script[2] = AcpSessionLimitReached("the hub keeps no more")
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/work")
    for n in (1, 2, 3):
        journal.record(S, MSG, {"text": str(n)})
    await journal.flush()
    assert hub.log(S) == [(1, "user_message", {"text": "1"})]  # what was kept stays
    assert journal.recording(S) is False
    assert channel.said == [f"Session history: {FULL}"]


async def test_a_defect_is_logged_and_the_event_kept(caplog: pytest.LogCaptureFixture) -> None:
    hub = FlakyHub()
    hub.script[1] = TypeError("a bug")
    journal = _journal(hub)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "a"})
    with caplog.at_level(logging.ERROR):
        await journal.flush()
    assert "keeping session" in caplog.text and "TypeError: a bug" in caplog.text
    await journal.flush()
    assert hub.log(S) == [(1, "user_message", {"text": "a"})]


async def test_only_an_open_session_is_kept_and_a_close_is_its_last_event() -> None:
    hub = FlakyHub()
    journal = _journal(hub)
    assert journal.record(S, MSG, {"text": "never opened"}) == 0
    journal.open(S, "/work")
    assert journal.record(S, MSG, {"text": "go"}) == 1
    assert journal.record(S, SessionEventKind.CLOSED, {}) == 2
    assert journal.record(S, MSG, {"text": "after the close"}) == 0
    await journal.flush()
    assert hub.log(S) == [(1, "user_message", {"text": "go"}), (2, "closed", {})]


async def test_a_session_is_kept_only_from_its_first_prompt() -> None:
    """A new session spends no slot of `[acp] sessions_max` until it is prompted: what is
    recorded before (a mode, the folder's project) waits, and goes with the first prompt."""
    hub = FlakyHub()
    journal = _journal(hub)
    journal.open(S, "/work")
    assert journal.record(S, SessionEventKind.ATTACH, {"projectId": "p"}) == 1
    assert journal.record(S, SessionEventKind.MODE, {"modeId": "observe"}) == 2
    await journal.flush()
    assert hub.session_calls == [] and journal.recording(S)
    assert journal.record(S, SessionEventKind.TITLE, {"title": "t"}) == 3
    assert journal.record(S, MSG, {"text": "go"}) == 4
    await journal.flush()
    assert hub.session_calls[0] == ("create", S)
    assert [kind for _, kind, _ in hub.log(S)] == ["attach", "mode", "title", "user_message"]


async def test_a_session_closed_before_any_prompt_is_never_kept() -> None:
    hub = FlakyHub()
    journal = _journal(hub)
    journal.open(S, "/work")
    journal.record(S, SessionEventKind.MODE, {"modeId": "observe"})
    assert journal.record(S, SessionEventKind.CLOSED, {}) == 0
    await journal.flush()
    assert hub.session_calls == [] and journal.recording(S) is False


async def test_what_waits_for_the_first_prompt_is_bounded() -> None:
    channel = FakeChannel()
    hub = FlakyHub()
    journal = _journal(hub, channel=channel, pending=2)
    journal.open(S, "/work")
    for mode in ("observe", "drive", "observe"):
        journal.record(S, SessionEventKind.MODE, {"modeId": mode})
    journal.record(S, MSG, {"text": "go"})
    await journal.flush()
    # Three held past the cap of two: the oldest goes; the prompt then queues the create and
    # three events past the cap, and the oldest go again. The create never does.
    assert hub.session_calls[0] == ("create", S)
    assert [seq for seq, _, _ in hub.log(S)] == [4]
    assert channel.said == [f"Session history: {OVERFLOW}"]


async def test_a_resume_never_lowers_the_next_seq() -> None:
    """A load whose flush failed but whose read succeeded resumes at the hub's newest seq while
    this process still holds later events: the next event follows those, it never collides."""
    hub = FlakyHub()
    hub.session_error = HubGatewayError("away")
    journal = _journal(hub)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "a"})
    journal.record(S, MSG, {"text": "b"})
    await journal.flush()
    journal.record(S, SessionEventKind.CLOSED, {})  # 3; the session stops being kept here
    journal.resume(S, 0)  # the hub knows nothing yet
    assert journal.record(S, MSG, {"text": "c"}) == 4
    hub.session_error = None
    await journal.flush()
    assert [seq for seq, _, _ in hub.log(S)] == [1, 2, 3, 4]


async def test_a_resumed_session_continues_after_its_last_seq() -> None:
    hub = FlakyHub()
    hub.kept[S] = ("/work", [])
    journal = _journal(hub)
    journal.resume(S, 7)
    assert journal.persisted_seq(S) == 7
    assert journal.record(S, MSG, {"text": "x"}) == 8
    journal.resume(S, 2)  # already kept here: its own seq stands
    assert journal.record(S, MSG, {"text": "y"}) == 9
    await journal.flush()
    assert [seq for seq, _, _ in hub.log(S)] == [8, 9]


async def test_a_closed_session_reopened_by_a_resume_is_kept_again() -> None:
    hub = FlakyHub()
    journal = _journal(hub)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "go"})
    journal.record(S, SessionEventKind.CLOSED, {})
    journal.resume(S, 2)
    assert journal.record(S, MSG, {"text": "back"}) == 3


# -- the channel a turn writes through ------------------------------------------------------


async def test_what_a_turn_showed_is_kept_once_the_client_was_sent_it() -> None:
    hub = FlakyHub()
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "go"})
    kept = AcpJournalingChannel(channel, journal, SESSION_REPLAY)
    mapper = AcpUpdateMapper()
    await kept.notify_update(S, mapper.agent_text("hi"))
    await kept.notify_update(S, mapper.tool_call_update("t1-1", ToolCallStatus.IN_PROGRESS))
    await kept.notify_update(S, mapper.current_mode("observe"))  # shown, not kept
    assert len(channel.updates) == 3
    await journal.flush()
    assert hub.log(S) == [
        (1, "user_message", {"text": "go"}),
        (2, "agent_message", {"text": "hi"}),
        (3, "tool_call_update", {"toolCallId": "t1-1", "status": "in_progress"}),
    ]


async def test_an_update_the_client_never_got_is_not_kept() -> None:
    class Gone(FakeChannel):
        async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
            raise BrokenPipeError("the client went away")

    journal = _journal(FlakyHub())
    journal.open(S, "/work")
    kept = AcpJournalingChannel(Gone(), journal, SESSION_REPLAY)
    with pytest.raises(BrokenPipeError):
        await kept.notify_update(S, AcpUpdateMapper().agent_text("hi"))
    assert journal.record(S, MSG, {"text": "next"}) == 1


async def test_permission_requests_pass_through_and_are_never_kept() -> None:
    channel = FakeChannel()
    channel.permission_answers = ["yes"]
    journal = _journal(FlakyHub())
    journal.open(S, "/work")
    kept = AcpJournalingChannel(channel, journal, SESSION_REPLAY)
    kept.client_capabilities = NOTICES
    assert channel.client_capabilities == NOTICES and kept.client_capabilities == NOTICES
    answer = await kept.request_permission(S, {"toolCallId": "x"}, [{"optionId": "yes"}], timeout=1)
    assert answer == "yes"
    assert kept.cancel_permissions(S) == ()
    assert channel.cancelled_permissions == [S]
    assert journal.record(S, MSG, {"text": "next"}) == 1


async def test_at_the_end_a_throttled_log_is_waited_for_within_a_bound() -> None:
    hub = FlakyHub()
    hub.script[2] = SessionWritesThrottled("429")
    hub.script[3] = SessionWritesThrottled("429")
    waits: list[float] = []

    async def wait(seconds: float) -> None:
        waits.append(seconds)

    journal = AcpSessionJournal(
        hub,
        AcpSettings(live_poll_seconds=1.0, probe_seconds=5),
        FakeChannel(),
        AcpUpdateMapper(),
        sleep=wait,
    )
    journal.open(S, "/work")
    for n in (1, 2, 3):
        journal.record(S, MSG, {"text": str(n)})
    await journal.drain()
    assert [seq for seq, _, _ in hub.log(S)] == [1, 2, 3]
    assert waits == [1.0, 2.0]


async def test_what_the_rate_limit_still_holds_at_the_end_is_said_never_lost_silently(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Throttled(FlakyHub):
        async def append_event(
            self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any]
        ) -> None:
            raise SessionWritesThrottled("429")

    waits: list[float] = []

    async def wait(seconds: float) -> None:
        waits.append(seconds)

    channel = FakeChannel()
    journal = AcpSessionJournal(
        Throttled(),
        AcpSettings(live_poll_seconds=1.0, probe_seconds=5),
        channel,
        AcpUpdateMapper(),
        sleep=wait,
    )
    journal.open(S, "/work")
    journal.record(S, MSG, {"text": "a"})
    journal.record(S, MSG, {"text": "b"})
    with caplog.at_level(logging.WARNING):
        await journal.drain()
    assert waits == [1.0, 2.0, 4.0]  # 7 s waited: past the 5 s bound, so it stops
    assert "2 ACP session event(s) were not kept" in caplog.text
    assert channel.said == [f"Session history: {UNSENT}"]


async def test_a_client_gone_at_the_end_does_not_stop_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Gone(FakeChannel):
        async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
            raise BrokenPipeError("the client went away")

    hub = FlakyHub()
    hub.script[1] = SessionEventConflict("taken")
    journal = _journal(hub, channel=Gone())
    journal.open(S, "/work")
    journal.open(T, "/work")
    journal.record(S, MSG, {"text": "a"})
    journal.record(T, MSG, {"text": "b"})
    with caplog.at_level(logging.WARNING):
        await journal.flush()
    assert hub.log(T) == [(1, "user_message", {"text": "b"})]
    assert "could not tell session" in caplog.text


async def test_past_the_cap_the_queue_keeps_every_create_and_drops_only_events() -> None:
    """With the hub away and a cap of one, two prompted sessions leave two creates queued: a
    create is never dropped, since every later event of its session needs it."""
    hub = FlakyHub()
    hub.session_error = HubGatewayError("away")
    journal = _journal(hub, pending=1)
    for session_id in (S, T):
        journal.open(session_id, "/work")
        journal.record(session_id, MSG, {"text": session_id})
    await journal.flush()
    hub.session_error = None
    await journal.flush()
    journal.record(S, MSG, {"text": "later"})
    await journal.flush()
    assert set(hub.kept) == {S, T}
    assert hub.log(T) == []
    assert [payload["text"] for _, _, payload in hub.log(S)] == ["later"]


async def test_a_session_in_a_folder_the_hub_would_refuse_is_never_queued() -> None:
    hub = FlakyHub()
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/bad\u200dfolder")
    journal.open(T, "/good")
    assert journal.recording(S) is False
    assert journal.record(S, MSG, {"text": "a"}) == 0
    journal.record(T, MSG, {"text": "b"})
    await journal.flush()
    assert set(hub.kept) == {T} and hub.log(T) == [(1, "user_message", {"text": "b"})]
    assert channel.sessions == [S] and channel.said == [f"Session history: {UNKEEPABLE_FOLDER}"]


class RefusingHub(FlakyHub):
    """Refuses, for good, the create or one append of session `S` only."""

    def __init__(self, *, on_create: bool) -> None:
        super().__init__()
        self.on_create = on_create

    async def create_session(self, session_id: str, cwd: str) -> None:
        if self.on_create and session_id == S:
            raise SessionRequestRefused("the hub refused it (422)")
        await super().create_session(session_id, cwd)

    async def append_event(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any]
    ) -> None:
        if not self.on_create and session_id == S and seq == 2:
            raise SessionRequestRefused("the hub refused it (413)")
        await super().append_event(session_id, seq, kind, payload)


@pytest.mark.parametrize("on_create", [True, False])
async def test_a_permanent_refusal_stops_that_session_only(
    on_create: bool, caplog: pytest.LogCaptureFixture
) -> None:
    """The refused session's log stops with one notice; the other's arrives, in order."""
    hub = RefusingHub(on_create=on_create)
    channel = FakeChannel()
    journal = _journal(hub, channel=channel)
    journal.open(S, "/work")
    journal.open(T, "/work")
    for n in (1, 2, 3):
        journal.record(S, MSG, {"text": f"s{n}"})
        journal.record(T, MSG, {"text": f"t{n}"})
    with caplog.at_level(logging.WARNING):
        await journal.flush()
    assert [payload["text"] for _, _, payload in hub.log(T)] == ["t1", "t2", "t3"]
    assert journal.recording(S) is False and journal.recording(T) is True
    assert channel.said == [f"Session history: {REFUSED}"]
    assert "the hub refused session" in caplog.text
    if not on_create:
        assert hub.log(S) == [(1, "user_message", {"text": "s1"})]  # what was kept stays
