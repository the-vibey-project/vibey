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
    SessionClosed,
    TurnAlreadyRunning,
)
from vibey.domain.errors import VibeyError

EVENTS = st.lists(
    st.sampled_from(["begin", "perm", "resolve", "cancel", "finish", "close"]), max_size=40
)


class _Model:
    """Drives one session through a list of events and records what the state machine says."""

    def __init__(self) -> None:
        self.state = AcpSessionState("s")
        self.begun = 0
        self.results: list[StopReason] = []
        self.cancel_ids_ok = True
        self.cancel_marks_ok = True
        self.finish_matches_cancel = True
        self._cancelled_this_turn = False
        self._counter = 0

    def apply(self, event: str) -> None:
        state = self.state
        self._counter += 1
        if event == "begin":
            try:
                state.begin_turn(f"t{self._counter}")
            except (TurnAlreadyRunning, SessionClosed):
                return
            self.begun += 1
            self._cancelled_this_turn = False
        elif event == "perm":
            try:
                state.register_permission(f"p{self._counter}")
            except NoActiveTurn:
                assert not state.turn_active
        elif event == "resolve":
            state.resolve_permission(next(iter(sorted(state.pending_permissions)), "none"))
        elif event == "cancel":
            before = state.pending_permissions
            active = state.turn_active
            ids = state.request_cancel()
            self.cancel_ids_ok &= set(ids) == (before if active else set()) and len(ids) == len(
                set(ids)
            )
            if active:
                self.cancel_marks_ok &= state.cancel_requested and not state.pending_permissions
                self._cancelled_this_turn = True
            else:
                self.cancel_marks_ok &= not state.cancel_requested
        elif event == "finish":
            try:
                result = state.finish_turn(StopReason.END_TURN)
            except NoActiveTurn:
                assert not state.turn_active
                return
            self.results.append(result)
            self.finish_matches_cancel &= (result is StopReason.CANCELLED) == (
                self._cancelled_this_turn
            )
            self._cancelled_this_turn = False
        else:
            # Closing cancels whatever turn is active; the turn still ends through finish_turn.
            self._cancelled_this_turn |= state.turn_active
            state.close()

    def settle(self) -> None:
        self.state.close()
        if self.state.turn_active:
            self.results.append(self.state.finish_turn(StopReason.END_TURN))
            self.finish_matches_cancel &= self.results[-1] is StopReason.CANCELLED


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
    assert model.cancel_ids_ok
    assert model.cancel_marks_ok
    assert model.finish_matches_cancel


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
