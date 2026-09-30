# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a project may be abandoned, and the words its record is made of (`vibey
abandon`). Pure: the phase machine's own guard decides, and a done project is refused."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from vibey.domain.abandonment import (
    ABANDONMENT_POLICY,
    GUARD,
    UNSETTLED_JOB_STATES,
    WITHDRAWN_REASON,
    AbandonmentPolicy,
    AbandonmentVerdict,
)
from vibey.domain.errors import AbandonmentRefused, InvalidAbandonment
from vibey.domain.interfaces import AbandonmentPolicyInterface
from vibey.domain.job import JobState
from vibey.domain.phase import TERMINAL, Phase, PhaseState, UnrecognizedPhase

AT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
PROJECT = UUID("9692abab-0000-4000-8000-000000000001")
GATE = UUID("9692abab-0000-4000-8000-000000000002")
JOB = UUID("9692abab-0000-4000-8000-000000000003")


def _state(phase: Phase | UnrecognizedPhase, *, cycle: int = 1, max_cycles: int = 3) -> PhaseState:
    return PhaseState(phase, cycle, max_cycles, AT)


def test_the_policy_satisfies_its_interface() -> None:
    assert isinstance(ABANDONMENT_POLICY, AbandonmentPolicyInterface)


def test_the_guard_and_the_unsettled_states_are_the_documented_ones() -> None:
    assert ABANDONMENT_POLICY.guard == GUARD == "operator abandoned"
    assert ABANDONMENT_POLICY.unsettled_states == {
        "ready",
        "leased",
        "awaiting_human",
        "awaiting_capacity",
    }
    # A settled job is history: an abandonment never touches one.
    settled = set(JobState) - UNSETTLED_JOB_STATES
    assert settled == {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}


@pytest.mark.parametrize("phase", sorted(set(Phase) - TERMINAL))
def test_every_phase_short_of_an_ending_may_be_abandoned(phase: Phase) -> None:
    """Derived from the enum, so a phase added later is covered without being listed --
    intake included: a project whose dispatch never reached DESIGN ends like any other."""
    assert ABANDONMENT_POLICY.decide(_state(phase)) is AbandonmentVerdict.ABANDON


def test_a_project_still_in_intake_may_be_abandoned() -> None:
    assert ABANDONMENT_POLICY.decide(_state(Phase.INTAKE)) is AbandonmentVerdict.ABANDON


def test_a_project_past_its_cycle_cap_may_still_be_abandoned() -> None:
    """The cycle cap stops every other move; abandoning is how such a project ends."""
    assert (
        ABANDONMENT_POLICY.decide(_state(Phase.BUILD, cycle=4, max_cycles=3))
        is AbandonmentVerdict.ABANDON
    )


def test_an_abandoned_project_is_already_abandoned_not_refused() -> None:
    assert (
        ABANDONMENT_POLICY.decide(_state(Phase.ABANDONED)) is AbandonmentVerdict.ALREADY_ABANDONED
    )


def test_a_done_project_is_refused_as_a_different_ending() -> None:
    with pytest.raises(AbandonmentRefused, match="the project is done"):
        ABANDONMENT_POLICY.decide(_state(Phase.DONE))


def test_a_phase_this_vibey_does_not_know_is_refused() -> None:
    with pytest.raises(AbandonmentRefused, match="'triage': 'triage' is not a phase"):
        ABANDONMENT_POLICY.decide(_state(UnrecognizedPhase("triage")))


def test_a_reason_is_stripped_and_kept_up_to_its_length() -> None:
    assert ABANDONMENT_POLICY.reason("  built on a foreign spec \n") == "built on a foreign spec"
    longest = "x" * AbandonmentPolicy.MAX_REASON_LENGTH
    assert ABANDONMENT_POLICY.reason(longest) == longest


@pytest.mark.parametrize(
    ("reason", "why"),
    [
        ("  \t ", "cannot be empty"),
        ("x" * (AbandonmentPolicy.MAX_REASON_LENGTH + 1), "is over 2000 characters"),
        ("wrong spec\nforged line", "cannot contain control or formatting"),
        ("wrong‮spec", "cannot contain control or formatting"),
    ],
)
def test_a_reason_that_cannot_be_recorded_is_refused(reason: str, why: str) -> None:
    with pytest.raises(InvalidAbandonment, match=why):
        ABANDONMENT_POLICY.reason(reason)


def test_the_actor_is_the_label_or_the_account_and_a_bad_label_is_refused() -> None:
    assert ABANDONMENT_POLICY.actor(None, account="adam") == "adam"
    assert ABANDONMENT_POLICY.actor(" vibey-vscode ", account="adam") == "vibey-vscode"
    with pytest.raises(InvalidAbandonment, match="the name an abandonment is recorded under"):
        ABANDONMENT_POLICY.actor("adam\nforged", account="adam")


def test_the_transition_attribution_names_who_why_and_what_it_stopped() -> None:
    assert ABANDONMENT_POLICY.transition_attribution(
        reason="foreign spec",
        by="vibey-vscode",
        account="adam",
        cancelled_jobs=[JOB],
        withdrawn_gates=[GATE],
    ) == {
        "reason": "foreign spec",
        "by": "vibey-vscode",
        "account": "adam",
        "cancelled_jobs": [str(JOB)],
        "withdrawn_gates": [str(GATE)],
    }


def test_a_withdrawn_gate_says_it_was_withdrawn_under_a_request_naming_the_project() -> None:
    assert ABANDONMENT_POLICY.withdrawn_answer() == {"withdrawn": True, "reason": WITHDRAWN_REASON}
    assert ABANDONMENT_POLICY.request_id(PROJECT) == f"abandon:{PROJECT}"


@pytest.mark.parametrize(("job_id", "stored"), [(JOB, str(JOB)), (None, None)])
def test_the_withdrawal_payload_names_the_gate_its_job_and_who(
    job_id: UUID | None, stored: str | None
) -> None:
    assert ABANDONMENT_POLICY.withdrawal_payload(
        gate_id=GATE,
        gate_kind="defect",
        job_id=job_id,
        request_id="abandon:x",
        by="adam",
        account="adam",
    ) == {
        "gate_id": str(GATE),
        "gate_kind": "defect",
        "job_id": stored,
        "request_id": "abandon:x",
        "reason": "project abandoned",
        "by": "adam",
        "account": "adam",
    }
