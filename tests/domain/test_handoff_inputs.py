# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which run inputs a handed-off run must be given (SP-LOOPS Phase 3c, Task 7). Module-level test
functions: the class-and-interface rule is about production code (ADR-0016)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from vibey.domain.handoff_inputs import HANDOFF_INPUTS, HandoffInputs
from vibey.domain.interfaces.handoff_inputs_interface import HandoffInputsInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.run_input import GIVEN_ARTIFACT_TYPE, HANDOFF_INPUTS_KEY

NOW = datetime(2026, 11, 23, tzinfo=UTC)
A, B, C = "a" * 64, "b" * 64, "c" * 64


def _event(
    seq: int,
    job_id: UUID | None,
    payload: dict[str, object],
    kind: EventKind = EventKind.ARTIFACT_PRODUCED,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=job_id,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=NOW,
        payload=payload,
        digest=digest_event(payload),
    )


def _given(seq: int, job_id: UUID | None, digests: object) -> LedgerEvent:
    return _event(seq, job_id, {"artifact_type": GIVEN_ARTIFACT_TYPE, "digests": digests})


def test_the_rule_meets_its_interface_and_the_key_is_fixed() -> None:
    assert isinstance(HANDOFF_INPUTS, HandoffInputsInterface)
    assert isinstance(HandoffInputs(), HandoffInputsInterface)
    assert HANDOFF_INPUTS_KEY == "handoff_input_digests"
    assert GIVEN_ARTIFACT_TYPE == "vibey_run_inputs_given"


def test_the_latest_given_event_of_the_job_is_the_pin() -> None:
    job = uuid4()
    events = [_given(9, job, [B, C]), _given(5, job, [A])]  # out of order on purpose
    assert HANDOFF_INPUTS.pinned(events, job) == (B, C)


def test_another_jobs_given_event_is_never_the_pin() -> None:
    job, other = uuid4(), uuid4()
    events = [_given(3, job, [A]), _given(8, other, [B]), _given(9, None, [C])]
    assert HANDOFF_INPUTS.pinned(events, job) == (A,)


def test_no_given_event_is_no_pin() -> None:
    job = uuid4()
    events = [
        _event(1, job, {"artifact_type": "vibey_run_input", "digest": A}),
        _event(
            2, job, {"artifact_type": GIVEN_ARTIFACT_TYPE, "digests": [A]}, EventKind.TURN_REQUESTED
        ),
    ]
    assert HANDOFF_INPUTS.pinned(events, job) is None
    assert HANDOFF_INPUTS.pinned((), job) is None


def test_an_empty_given_list_is_an_empty_pin() -> None:
    job = uuid4()
    assert HANDOFF_INPUTS.pinned([_given(1, job, [])], job) == ()


@pytest.mark.parametrize("digests", [["A" * 64], ["abc"], [7], "a" * 64, None, {"d": A}])
def test_a_given_event_with_a_digest_that_is_not_hex_is_refused(digests: object) -> None:
    job = uuid4()
    with pytest.raises(ValueError, match="does not list digests"):
        HANDOFF_INPUTS.pinned([_given(4, job, digests)], job)
