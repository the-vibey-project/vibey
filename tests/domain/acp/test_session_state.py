# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP session's turn, cancel and permission state machine (SP-ACP, Task 2).

The properties pin the two failure modes the plan's Review Focus names for it: a turn that
ends with no stop reason or two, and a cancel that leaves a permission request pending or
leaks into the next turn."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface
from vibey.domain.acp.protocol import StopReason
from vibey.domain.acp.session_state import (
    AcpSessionState,
    NoActiveTurn,
    PermissionsStillPending,
    SessionClosed,
    TurnAlreadyRunning,
    TurnCancelled,
)
from vibey.domain.errors import VibeyError

EVENTS = st.lists(
    st.sampled_from(["begin", "perm", "resolve", "cancel", "finish", "close"]), max_size=40
)


class _Model:
    """Drives one session through a list of events against an independent oracle.

    `expected_pending` is the model's own record of which permission ids are out; it never
    reads the implementation's, so a register or resolve that does nothing is caught."""

    def __init__(self) -> None:
        self.state = AcpSessionState("s")
        self.begun = 0
        self.results: list[StopReason] = []
        self.expected_pending: set[str] = set()
        self.finish_matches_cancel = True
        self._cancelled_this_turn = False
        self._counter = 0

    def check(self) -> None:
        assert self.state.pending_permissions == self.expected_pending

    def apply(self, event: str) -> None:
        self._counter += 1
        getattr(self, f"_{event}")(f"p{self._counter}")
        self.check()

    def _begin(self, ident: str) -> None:
        try:
            self.state.begin_turn(f"t{ident}")
        except (TurnAlreadyRunning, SessionClosed):
            return
        self.begun += 1
        self._cancelled_this_turn = False

    def _perm(self, ident: str) -> None:
        active = self.state.turn_active
        try:
            self.state.register_permission(ident)
        except NoActiveTurn:
            assert not active
        except TurnCancelled:
            assert active
            assert self._cancelled_this_turn
        else:
            assert active
            assert not self._cancelled_this_turn
            self.expected_pending.add(ident)

    def _resolve(self, ident: str) -> None:
        target = min(self.expected_pending, default="none")
        self.state.resolve_permission(target)
        self.expected_pending.discard(target)

    def _cancel(self, ident: str) -> None:
        active = self.state.turn_active
        ids = self.state.request_cancel()
        assert set(ids) == (self.expected_pending if active else set())
        assert len(ids) == len(set(ids))
        self.expected_pending.clear()
        if active:
            assert self.state.cancel_requested
            self._cancelled_this_turn = True
        else:
            assert not self.state.cancel_requested

    def _finish(self, ident: str) -> None:
        try:
            result = self.state.finish_turn(StopReason.END_TURN)
        except NoActiveTurn:
            assert not self.state.turn_active
            return
        except PermissionsStillPending:
            assert self.state.turn_active
            assert self.expected_pending
            assert not self._cancelled_this_turn
            return
        assert not self.expected_pending
        self.results.append(result)
        self.finish_matches_cancel &= (result is StopReason.CANCELLED) == (
            self._cancelled_this_turn
        )
        self._cancelled_this_turn = False

    def _close(self, ident: str) -> None:
        active = self.state.turn_active
        ids = self.state.close()
        assert set(ids) == (self.expected_pending if active else set())
        self.expected_pending.clear()
        self._cancelled_this_turn |= active

    def settle(self) -> None:
        self._close("end")
        if self.state.turn_active:
            self.results.append(self.state.finish_turn(StopReason.END_TURN))
            self.finish_matches_cancel &= self.results[-1] is StopReason.CANCELLED
            self._cancelled_this_turn = False
        self.check()


@given(EVENTS)
def test_every_begun_turn_ends_with_exactly_one_stop_reason(events: list[str]) -> None:
    model = _Model()
    for event in events:
        model.apply(event)
    model.settle()
    assert model.begun == len(model.results)
    assert all(isinstance(result, StopReason) for result in model.results)
    assert not model.state.turn_active
    assert model.state.pending_permissions == frozenset()


@given(EVENTS)
def test_cancel_always_resolves_every_pending_permission(events: list[str]) -> None:
    model = _Model()
    for event in events:
        model.apply(event)
    model.settle()
    assert model.finish_matches_cancel


def test_a_permission_after_a_cancel_is_refused_and_leaves_nothing_pending() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.request_cancel()
    with pytest.raises(TurnCancelled) as error:
        s.register_permission("late")
    assert isinstance(error.value, VibeyError)
    assert s.pending_permissions == frozenset()


def test_a_permission_after_close_is_refused() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.close()
    with pytest.raises(TurnCancelled):
        s.register_permission("late")
    s.finish_turn(StopReason.END_TURN)
    with pytest.raises(NoActiveTurn):
        s.register_permission("later")


def test_finishing_a_turn_with_a_permission_out_is_refused_and_keeps_the_turn() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.register_permission("a")
    with pytest.raises(PermissionsStillPending, match="a") as error:
        s.finish_turn(StopReason.END_TURN)
    assert isinstance(error.value, VibeyError)
    assert s.turn_active
    assert s.pending_permissions == frozenset({"a"})
    s.resolve_permission("a")
    assert s.finish_turn(StopReason.END_TURN) is StopReason.END_TURN


def test_cancel_returns_the_pending_ids_and_the_turn_finishes_cancelled() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.register_permission("b")
    s.register_permission("a")
    assert s.request_cancel() == ("a", "b")
    assert s.pending_permissions == frozenset()
    assert s.cancel_requested
    assert s.finish_turn(StopReason.END_TURN) is StopReason.CANCELLED
    assert not s.turn_active
    assert not s.cancel_requested


def test_a_late_answer_to_a_cancelled_permission_is_ignored() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.register_permission("a")
    s.request_cancel()
    s.resolve_permission("a")
    assert s.pending_permissions == frozenset()


def test_cancel_without_a_turn_does_not_leak_into_the_next_turn() -> None:
    s = AcpSessionState("s")
    assert s.request_cancel() == ()
    s.begin_turn("t1")
    assert not s.cancel_requested
    assert s.finish_turn(StopReason.END_TURN) is StopReason.END_TURN


def test_a_cancel_of_one_turn_does_not_leak_into_the_next() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.request_cancel()
    assert s.finish_turn(StopReason.MAX_TOKENS) is StopReason.CANCELLED
    s.begin_turn("t2")
    assert s.finish_turn(StopReason.MAX_TOKENS) is StopReason.MAX_TOKENS


def test_resolve_removes_only_that_permission() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.register_permission("a")
    s.register_permission("b")
    s.resolve_permission("a")
    assert s.pending_permissions == frozenset({"b"})
    s.resolve_permission("b")
    assert s.finish_turn(StopReason.REFUSAL) is StopReason.REFUSAL
    assert s.pending_permissions == frozenset()


def test_a_second_begin_while_active_is_refused() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    with pytest.raises(TurnAlreadyRunning) as error:
        s.begin_turn("t2")
    assert isinstance(error.value, VibeyError)
    assert s.turn_active


def test_permission_and_finish_outside_a_turn_are_refused() -> None:
    s = AcpSessionState("s")
    with pytest.raises(NoActiveTurn):
        s.register_permission("a")
    with pytest.raises(NoActiveTurn):
        s.finish_turn(StopReason.END_TURN)


def test_close_is_idempotent_and_refuses_new_turns() -> None:
    s = AcpSessionState("s")
    s.begin_turn("t1")
    s.register_permission("a")
    assert s.close() == ("a",)
    assert s.closed
    assert s.cancel_requested
    assert s.close() == ()
    assert s.finish_turn(StopReason.END_TURN) is StopReason.CANCELLED
    with pytest.raises(SessionClosed) as error:
        s.begin_turn("t2")
    assert isinstance(error.value, VibeyError)


def test_close_with_no_turn_is_a_clean_no_op() -> None:
    s = AcpSessionState("s")
    assert s.close() == ()
    assert s.closed
    assert not s.turn_active


def test_the_session_id_is_kept() -> None:
    assert AcpSessionState("abc").session_id == "abc"


def test_the_implementation_satisfies_its_interface() -> None:
    assert isinstance(AcpSessionState("s"), AcpSessionStateInterface)
