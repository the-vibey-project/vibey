# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpLiveFeed`: a project's ledger as a phase plan and messages, by watermark (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import pytest
from acp_fakes import FakeChannel, FakeHub, context, event, page, until

from vibey.application.acp.acp_live_feed import LIVE_PAGE, AcpLiveFeed
from vibey.application.acp.dto import AcpSessionContext
from vibey.application.acp.interfaces.acp_live_feed_interface import AcpLiveFeedInterface
from vibey.domain.acp.protocol import StopReason
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError

PID = UUID("11111111-1111-4111-8111-111111111111")
OTHER = UUID("22222222-2222-4222-8222-222222222222")
SPEND_GATE = "33333333-3333-4333-8333-333333333333"


class Sleeps:
    """Stands in for `asyncio.sleep`: records each wait and only yields to the loop."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)
        await asyncio.sleep(0)


def build(
    channel: FakeChannel, hub: FakeHub, *, settings: AcpSettings | None = None
) -> tuple[AcpLiveFeed, Sleeps]:
    sleeps = Sleeps()
    feed = AcpLiveFeed(hub, channel, AcpUpdateMapper(), settings or AcpSettings(), sleep=sleeps)
    return feed, sleeps


def seqs(channel: FakeChannel) -> list[int]:
    return [int(m.group(1)) for t in channel.said for m in [re.search(r": e(\d+)$", t)] if m]


def plans(channel: FakeChannel) -> list[list[tuple[str, str]]]:
    return [
        [(e["content"], e["status"]) for e in update["entries"]]
        for update in channel.updates
        if update["sessionUpdate"] == "plan"
    ]


async def run_until(
    work: Awaitable[None], predicate: Callable[[], bool], spins: int = 2000
) -> None:
    task = asyncio.ensure_future(work)
    try:
        await until(predicate, spins)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


def attached(session_id: str = "s", project: UUID = PID) -> AcpSessionContext:
    session = context(session_id)
    session.state.finish_turn(StopReason.END_TURN)  # between turns, as after session/new
    session.project_id = project
    return session


def test_the_feed_satisfies_its_interface() -> None:
    assert isinstance(build(FakeChannel(), FakeHub())[0], AcpLiveFeedInterface)


async def test_live_stream_resumes_from_watermark_without_duplicates() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [
        page(event(1), event(2), event(3)),
        HubGatewayError("hub restarting"),
        page(event(3), event(4)),  # overlap after a hub restart
    ]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: seqs(channel) == [1, 2, 3, 4])

    assert seqs(channel) == [1, 2, 3, 4] and feed.watermark("s") == 4
    assert [call[1] for call in hub.ledger_calls[:3]] == [0, 3, 3]


async def test_failed_poll_leaves_watermark_unmoved() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page(event(5)), HubGatewayError("down"), HubGatewayError("still down")]
    feed, sleeps = build(channel, hub, settings=AcpSettings(live_poll_seconds=0.5))

    await run_until(feed.follow("s", PID, after=4), lambda: len(hub.ledger_calls) >= 4)

    assert feed.watermark("s") == 5
    assert [call[1] for call in hub.ledger_calls[:4]] == [4, 5, 5, 5]
    paused = [t for t in channel.said if t.startswith("Live updates paused")]
    assert len(paused) == 1 and "down" in paused[0]  # reported once, not once per poll
    assert "Live updates resumed." in channel.said
    # A short page waits live_poll_seconds; failures in a row wait 0.5 then 1.0 (doubling);
    # once a read works again the wait is back to 0.5. Never a tight loop.
    assert sleeps.waits[:4] == [0.5, 0.5, 1.0, 0.5]


async def test_an_event_at_or_below_the_watermark_is_skipped() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page(event(2), event(3), event(9))]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=3), lambda: feed.watermark("s") == 9)

    assert seqs(channel) == [9]


async def test_an_event_without_a_usable_seq_is_skipped() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page({"seq": "4", "phase": "build"}, {"seq": True}, event(5))]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 5)

    assert seqs(channel) == [5]


async def test_the_watermark_moves_only_after_the_update_was_sent() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page(event(1, phase="design"), event(2, phase="design"))]
    released = asyncio.Event()
    channel.hold_before[3] = released  # plan, e1, then e2 waits to be written
    feed, _ = build(channel, hub)
    task = asyncio.ensure_future(feed.follow("s", PID, after=0))
    try:
        await until(channel.write_waiting.is_set)
        assert feed.watermark("s") == 1
        released.set()
        await until(lambda: feed.watermark("s") == 2)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_a_full_page_is_read_again_at_once() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.ledger = [event(seq) for seq in range(1, LIVE_PAGE + 3)]
    feed, sleeps = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == LIVE_PAGE + 2)

    assert hub.ledger_calls == [(PID, 0, LIVE_PAGE), (PID, LIVE_PAGE, LIVE_PAGE)]
    assert sleeps.waits == [1.0]  # no wait after the full page, one after the short one


async def test_plan_is_resent_only_on_phase_change() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [
        page(
            event(1, phase="design"),
            event(2, phase="design"),
            event(3, phase="build"),
            event(4, phase="build"),
            event(5, phase="review"),
            event(6, phase="build"),
        )
    ]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 6)

    assert len(plans(channel)) == 4
    assert plans(channel)[-1][:3] == [
        ("Design", "completed"),
        ("Build", "in_progress"),
        ("Review", "pending"),
    ]
    kinds = [u["sessionUpdate"] for u in channel.updates]
    # The plan goes out just before the first event of a new phase.
    assert kinds[:4] == ["plan", "agent_message_chunk", "agent_message_chunk", "plan"]


async def test_abandoning_keeps_the_plan_and_says_so_once() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [
        page(
            event(1, phase="build"),
            event(2, phase="abandoned", kind="PhaseTransitioned"),
            event(3, phase="abandoned", kind="GateWithdrawn"),
        )
    ]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 3)

    assert channel.said.count("Project abandoned.") == 1
    assert plans(channel)[-1][:2] == [("Design", "completed"), ("Build", "in_progress")]


async def test_between_turn_events_are_buffered_when_configured() -> None:
    channel, hub = FakeChannel(), FakeHub()
    settings = AcpSettings(live_between_turns=False)
    feed, _ = build(channel, hub, settings=settings)
    session = attached()
    hub.ledger = [event(1, phase="design")]

    feed.attach(session)
    await until(lambda: feed.watermark("s") == 1)  # the plan at attach time
    hub.ledger += [event(2, phase="design"), event(3, phase="build")]
    await until(lambda: len(hub.ledger_calls) >= 6)

    assert seqs(channel) == [] and feed.watermark("s") == 1
    session.state.begin_turn("t2")
    await feed.flush("s")

    assert seqs(channel) == [2, 3] and feed.watermark("s") == 3
    await feed.close()


async def test_events_during_a_turn_stream_even_when_buffering() -> None:
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub, settings=AcpSettings(live_between_turns=False))
    session = attached()
    session.state.begin_turn("t2")

    feed.attach(session)
    await until(lambda: feed.watermark("s") == 0 and len(hub.ledger_calls) >= 1)
    hub.ledger = [event(1)]
    await until(lambda: seqs(channel) == [1])

    assert feed.watermark("s") == 1  # sent during the turn, not held for the next one
    await feed.close()


async def test_the_buffer_is_bounded_and_nothing_past_it_is_skipped() -> None:
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(
        channel, hub, settings=AcpSettings(live_between_turns=False, pending_events_max=2)
    )
    session = attached()
    feed.attach(session)
    await until(lambda: len(hub.ledger_calls) >= 1)
    hub.ledger = [event(seq) for seq in range(1, 6)]
    for _ in range(50):
        await asyncio.sleep(0)

    assert hub.ledger_calls[0][2] == LIVE_PAGE  # the catch-up holds nothing
    assert all(limit <= 2 for _, _, limit in hub.ledger_calls[1:])
    # With two held, nothing past them is read: the watermark never skips past the third.
    assert {after for _, after, _ in hub.ledger_calls} == {0}
    assert seqs(channel) == []
    session.state.begin_turn("t2")
    await feed.flush("s")
    assert seqs(channel) == [1, 2]
    await until(lambda: seqs(channel) == [1, 2, 3, 4, 5])
    await feed.close()


async def test_flush_with_nothing_held_sends_nothing() -> None:
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub)

    await feed.flush("nobody")

    assert channel.updates == [] and feed.watermark("nobody") == 0


async def test_attach_catches_up_without_replaying_and_sends_the_plan_once() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.ledger = [
        event(1, phase="intake"),
        event(2, phase="design"),
        event(3, phase="visual_design"),
        event(4, phase="build"),
    ]
    feed, _ = build(channel, hub)

    feed.attach(attached())
    await until(lambda: feed.watermark("s") == 4)

    assert seqs(channel) == []  # history is read for the plan, never replayed as messages
    assert plans(channel) == [
        [
            ("Design", "completed"),
            ("Visual design", "completed"),
            ("Build", "in_progress"),
            ("Review", "pending"),
            ("Deploy design", "pending"),
            ("Deploy execute", "pending"),
            ("Deploy review", "pending"),
        ]
    ]
    hub.ledger.append(event(5))
    await until(lambda: seqs(channel) == [5])
    assert len(plans(channel)) == 1
    await feed.close()


async def test_attach_reads_a_long_ledger_to_its_end() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.ledger = [event(seq, phase="review") for seq in range(1, 2 * LIVE_PAGE + 2)]
    feed, _ = build(channel, hub)

    feed.attach(attached())
    await until(lambda: feed.watermark("s") == 2 * LIVE_PAGE + 1)

    assert [call[1] for call in hub.ledger_calls[:3]] == [0, LIVE_PAGE, 2 * LIVE_PAGE]
    await feed.close()


async def test_attach_to_an_empty_ledger_sends_no_plan() -> None:
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub)

    feed.attach(attached())
    await until(lambda: len(hub.ledger_calls) >= 3)

    assert channel.updates == [] and feed.watermark("s") == 0
    await feed.close()


async def test_attach_to_an_abandoned_project_says_so() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.ledger = [event(1, phase="design"), event(2, phase="abandoned")]
    feed, _ = build(channel, hub)

    feed.attach(attached())
    await until(lambda: feed.watermark("s") == 2)

    assert channel.said == ["Project abandoned."]
    await feed.close()


async def test_a_failed_catch_up_is_reported_once_and_retried() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [HubGatewayError("down"), HubGatewayError("down")]
    hub.ledger = [event(1, phase="design")]
    feed, sleeps = build(channel, hub)

    feed.attach(attached())
    await until(lambda: feed.watermark("s") == 1)

    assert [t for t in channel.said if t.startswith("Live updates")] == [
        "Live updates paused: the project's ledger could not be read (down). "
        "Retrying, waiting longer each time, up to 30 s.",
        "Live updates resumed.",
    ]
    assert len(sleeps.waits) >= 2
    await feed.close()


async def test_reattaching_cancels_the_previous_feed() -> None:
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub)
    session = attached()
    feed.attach(session)
    await until(lambda: len(hub.ledger_calls) >= 2)

    session.project_id = OTHER
    feed.attach(session)
    hub.ledger_calls.clear()
    await until(lambda: len(hub.ledger_calls) >= 3)

    assert {call[0] for call in hub.ledger_calls} == {OTHER}
    await feed.close()


async def test_detach_stops_the_feed_and_close_leaves_no_task() -> None:
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub)
    feed.attach(attached("a"))
    feed.attach(attached("b"))
    await until(lambda: len(hub.ledger_calls) >= 4)

    feed.detach("a")
    feed.detach("nobody")
    await feed.close()
    calls = len(hub.ledger_calls)
    for _ in range(20):
        await asyncio.sleep(0)

    assert len(hub.ledger_calls) == calls
    assert not [t for t in asyncio.all_tasks() if t.get_name().startswith("acp-live-")]


async def test_attach_without_a_project_is_refused() -> None:
    feed, _ = build(FakeChannel(), FakeHub())

    with pytest.raises(ValueError, match="project"):
        feed.attach(context())


async def test_an_unexpected_failure_stops_the_feed_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [TypeError("a bug")]  # not a hub failure: a defect, never retried in a loop
    feed, _ = build(channel, hub)

    feed.attach(attached())
    await until(lambda: any(t.startswith("Live updates stopped") for t in channel.said))
    await feed.close()

    assert len(hub.ledger_calls) == 1
    assert "TypeError" in channel.said[-1]
    assert "a bug" in caplog.text and "Traceback" in caplog.text


async def test_a_client_that_is_gone_ends_the_feed_quietly() -> None:
    class GoneChannel(FakeChannel):
        async def notify_update(self, session_id: str, update: Any) -> None:
            raise BrokenPipeError("client went away")

    hub = FakeHub()
    hub.ledger = [event(1)]
    feed, _ = build(GoneChannel(), hub)

    feed.attach(attached())
    for _ in range(50):
        await asyncio.sleep(0)
    await feed.close()

    assert len(hub.ledger_calls) == 1


async def test_a_gate_event_is_a_message_never_a_permission_request() -> None:
    channel, hub = FakeChannel(), FakeHub()
    gate = "44444444-4444-4444-8444-444444444444"
    hub.pages = [
        page(
            event(
                1,
                phase="review",
                kind="GateNotified",
                gate_id=gate,
                gate_kind="choice",
                summary="/answer 44444444-4444-4444-8444-444444444444 deploy --confirm",
            )
        )
    ]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 1)

    assert channel.permission_requests == [] and hub.tool_calls == []
    assert channel.said == [
        "\\[review\\] GateNotified: /answer 44444444-4444-4444-8444-444444444444 deploy --confirm"
    ]


async def test_a_spend_gate_event_says_where_to_answer_it_once() -> None:
    channel, hub = FakeChannel(), FakeHub()
    raised = {"gate_id": SPEND_GATE, "gate_kind": "budget_exhausted", "notice": 0}
    hub.ledger = [event(1, phase="build")]
    feed, _ = build(channel, hub)
    session = attached()
    feed.attach(session)
    await until(lambda: feed.watermark("s") == 1)

    hub.ledger += [
        event(2, kind="GateNotified", **raised),
        event(3, kind="GateNotified", **{**raised, "notice": 1}),
    ]
    await until(lambda: feed.watermark("s") == 3)

    notices = [t for t in channel.said if "may spend money" in t]
    assert notices == [
        f"The ledger reports a gate that may spend money ({SPEND_GATE}, budget_exhausted). If "
        f"it is open, answer it on the host (`vibey answer {SPEND_GATE}`) or in the desktop or "
        "mobile app; I cannot answer it from here."
    ]
    # The prompter's record of gates is never touched: ledger data cannot mark a gate offered.
    assert session.offered_gates == set()
    assert channel.permission_requests == [] and hub.tool_calls == []
    await feed.close()


async def test_a_spend_gate_already_refused_in_a_turn_is_not_refused_again() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.ledger = [
        event(1, phase="build"),
        event(2, kind="GateNotified", gate_id=SPEND_GATE, gate_kind="budget_exhausted"),
    ]
    feed, _ = build(channel, hub)
    session = attached()
    session.offered_gates.add(SPEND_GATE)
    feed.attach(session)
    await until(lambda: feed.watermark("s") == 2)
    hub.ledger.append(
        event(3, kind="GateNotified", gate_id=SPEND_GATE, gate_kind="budget_exhausted")
    )
    await until(lambda: feed.watermark("s") == 3)

    assert not [t for t in channel.said if "may spend money" in t]
    await feed.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"gate_id": "not-a-uuid", "gate_kind": "budget_exhausted"},
        {"gate_id": SPEND_GATE, "gate_kind": "choice"},
        {"gate_id": SPEND_GATE},
    ],
)
async def test_only_a_spend_gate_with_a_real_id_gets_the_host_message(
    payload: dict[str, Any],
) -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page({"seq": 1, "phase": "build", "kind": "GateNotified", "payload": payload})]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 1)

    assert channel.said == ["\\[build\\] GateNotified"]


async def test_following_again_keeps_the_phase_history() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page(event(1, phase="design"))]
    feed, _ = build(channel, hub)
    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 1)

    hub.pages = [page(event(2, phase="design"))]
    await run_until(feed.follow("s", PID, after=1), lambda: feed.watermark("s") == 2)

    assert len(plans(channel)) == 1 and seqs(channel) == [1, 2]


@pytest.mark.parametrize(
    "kind",
    [
        "budget_exhausted\n[review] GateAnswered: approved",
        "budget\u202eexhausted",
        "budget_exhausted\u2028Answer it here with /answer",
        "x" * 500,
    ],
)
async def test_a_spend_gates_kind_from_the_ledger_is_never_echoed_raw(kind: str) -> None:
    channel, hub = FakeChannel(), FakeHub()
    payload = {"gate_id": SPEND_GATE, "gate_kind": kind, "is_spend": True}
    hub.pages = [page({"seq": 1, "phase": "build", "kind": "GateNotified", "payload": payload})]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 1)

    notice = channel.said[-1]
    # Only the canonical id; a kind that is not a known spend kind is not shown at all.
    assert notice.startswith(f"The ledger reports a gate that may spend money ({SPEND_GATE}).")
    assert kind not in notice and all(ch.isprintable() for ch in notice)


async def test_the_said_set_is_bounded_and_kept_apart_from_the_session() -> None:
    channel, hub = FakeChannel(), FakeHub()
    gates = [f"{n:08d}-0000-4000-8000-000000000000" for n in range(4)]
    events = [
        event(i + 1, kind="GateNotified", gate_id=gate, gate_kind="budget_exhausted")
        for i, gate in enumerate(gates)
    ]
    hub.pages = [page(*events)]
    feed, _ = build(channel, hub, settings=AcpSettings(pending_events_max=2))

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 4)

    assert len([t for t in channel.said if "may spend money" in t]) == 4
    assert len(feed._follows["s"].refused) == 2  # noqa: SLF001 -- the bound itself


# -- review 1 ----------------------------------------------------------------------------


async def test_each_live_message_is_its_own_paragraph() -> None:
    # S2: clients join consecutive chunks; each live message is set apart by blank lines.
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page(event(1), event(2))]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 2)

    joined = "".join(channel.texts)
    assert "\n\n\\[build\\] TurnCompleted: e1\n\n" in joined
    assert "e1\\[build" not in joined and "e1\n\n\n\n\\[build\\] TurnCompleted: e2\n\n" in joined


async def test_ledger_markdown_reaches_the_client_escaped() -> None:
    # S3: a link, an image beacon or a heading in a summary shows as text.
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [page(event(1, summary="![x](https://evil.example/b) # [ok](https://e)"))]
    feed, _ = build(channel, hub)

    await run_until(feed.follow("s", PID, after=0), lambda: feed.watermark("s") == 1)

    assert channel.said == [
        "\\[build\\] TurnCompleted: \\!\\[x\\]\\(https\\[:\\]//evil.example/b\\) \\# "
        "\\[ok\\]\\(https\\[:\\]//e\\)"
    ]


async def test_the_retry_wait_doubles_up_to_the_keep_alive_interval() -> None:
    # S6: hub-down retries back off, capped at [acp] probe_seconds.
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [HubGatewayError("down")] * 8
    feed, sleeps = build(channel, hub, settings=AcpSettings(live_poll_seconds=1.0, probe_seconds=5))

    await run_until(feed.follow("s", PID, after=0), lambda: len(sleeps.waits) >= 8)

    assert sleeps.waits[:6] == [1.0, 2.0, 4.0, 5.0, 5.0, 5.0]
    assert channel.said[0].endswith("Retrying, waiting longer each time, up to 5 s.")


async def test_the_paused_message_shows_the_hubs_error_as_safe_text() -> None:
    # N8: the error text is hub data: one line, escaped, capped.
    channel, hub = FakeChannel(), FakeHub()
    hub.pages = [HubGatewayError("hub refused (500): [x](https://e)\n" + "y" * 900)]
    feed, _ = build(channel, hub, settings=AcpSettings(live_message_chars=40))

    await run_until(feed.follow("s", PID, after=0), lambda: bool(channel.updates))

    paused = channel.said[0]
    assert "\\[x\\]\\(https\\[:\\]//e\\)" in paused and "\n" not in paused
    assert "y" * 40 not in paused


class WaitCountingHub(FakeHub):
    """Records, for each read, how many waits the feed had made before it."""

    def __init__(self, sleeps: Sleeps) -> None:
        super().__init__()
        self.sleeps = sleeps
        self.waits_before: list[int] = []

    async def ledger_after(self, project_id: UUID, after: int, limit: int) -> Any:
        self.waits_before.append(len(self.sleeps.waits))
        return await super().ledger_after(project_id, after, limit)


async def test_a_full_page_that_does_not_advance_is_not_reread_at_once() -> None:
    # N1: judged by progress as well as length.
    sleeps = Sleeps()
    hub = WaitCountingHub(sleeps)
    stale = tuple(event(seq) for seq in range(1, LIVE_PAGE + 1))
    hub.pages = [page(*stale), page(*stale), page(*stale)]
    feed = AcpLiveFeed(hub, FakeChannel(), AcpUpdateMapper(), AcpSettings(), sleep=sleeps)

    await run_until(feed.follow("s", PID, after=0), lambda: len(hub.ledger_calls) >= 4)

    # The first page advanced: read again at once. The stale ones did not: each waited.
    assert hub.waits_before[:4] == [0, 0, 1, 2]


async def test_a_catch_up_page_that_does_not_advance_ends_the_catch_up() -> None:
    sleeps = Sleeps()
    hub = WaitCountingHub(sleeps)
    hub.pages = [page(*[{"seq": "x", "phase": "build"}] * LIVE_PAGE)] * 4
    feed = AcpLiveFeed(hub, FakeChannel(), AcpUpdateMapper(), AcpSettings(), sleep=sleeps)

    feed.attach(attached())
    await until(lambda: len(hub.ledger_calls) >= 4)

    # One catch-up read, then the poll, which waits after each read that did not advance.
    assert hub.waits_before[:4] == [0, 0, 1, 2] and feed.watermark("s") == 0
    await feed.close()


async def test_a_plan_cut_off_by_a_cancel_is_sent_when_the_event_is_redelivered() -> None:
    # N2: the history takes a phase only after its plan went out.
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub, settings=AcpSettings(live_between_turns=False))
    session = attached()
    hub.ledger = [event(1, phase="design")]
    feed.attach(session)
    await until(lambda: feed.watermark("s") == 1)
    hub.ledger.append(event(2, phase="build"))
    await until(lambda: len(hub.ledger_calls) >= 4)
    held = asyncio.Event()
    channel.hold_before[len(channel.updates) + 1] = held  # the build plan waits to be written
    # Between turns the loop only holds; this flush is the one drain writing.
    flushing = asyncio.ensure_future(feed.flush("s"))
    await until(channel.write_waiting.is_set)

    flushing.cancel()  # session/cancel lands while the plan is written
    with pytest.raises(asyncio.CancelledError):
        await flushing
    await feed.flush("s")

    assert plans(channel)[-1][:2] == [("Design", "completed"), ("Build", "in_progress")]
    assert seqs(channel) == [2] and feed.watermark("s") == 2
    await feed.close()


async def test_following_a_session_already_attached_is_refused() -> None:
    # N3: a second loop could move the watermark backwards.
    feed, _ = build(FakeChannel(), FakeHub())
    feed.attach(attached())

    with pytest.raises(ValueError, match="already followed"):
        await feed.follow("s", PID, after=0)
    await feed.close()


async def test_a_drain_stops_when_the_feed_is_detached_under_it() -> None:
    # N10: a flush that waited sends none of the old project's events after the move.
    channel, hub = FakeChannel(), FakeHub()
    feed, _ = build(channel, hub, settings=AcpSettings(live_between_turns=False))
    session = attached()
    feed.attach(session)
    await until(lambda: len(hub.ledger_calls) >= 1)
    hub.ledger = [event(1), event(2)]
    await until(lambda: len(hub.ledger_calls) >= 4)
    held = asyncio.Event()
    channel.hold_before[len(channel.updates) + 1] = held
    # Between turns the loop only holds; this flush is the one drain writing.
    flushing = asyncio.ensure_future(feed.flush("s"))
    await until(channel.write_waiting.is_set)

    feed.detach("s")
    held.set()
    await flushing

    assert seqs(channel) == [1]  # the one already being written, and no more
    await feed.close()
