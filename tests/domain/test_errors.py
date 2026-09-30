# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from uuid import UUID

from vibey.domain.errors import (
    BudgetExceeded,
    CheckoutHeld,
    EscalationExhausted,
    HandoffRejected,
    IllegalTransitionError,
    InvalidPhaseError,
    InvalidSpecError,
    NoEligibleEngine,
    SovereignResearchUnavailable,
    VibeyError,
)


def test_vibey_error_is_an_exception() -> None:
    assert issubclass(VibeyError, Exception)


def test_error_hierarchy_all_descend_from_vibey_error() -> None:
    for exc_type in (
        InvalidPhaseError,
        IllegalTransitionError,
        NoEligibleEngine,
        EscalationExhausted,
        HandoffRejected,
        InvalidSpecError,
        BudgetExceeded,
    ):
        assert issubclass(exc_type, VibeyError)


def test_escalation_exhausted_carries_the_attempt_number() -> None:
    error = EscalationExhausted(7)

    assert error.attempt == 7
    assert "7" in str(error)


def test_handoff_rejected_carries_the_gate_result() -> None:
    class _FakeGateResult:
        violations = ("v1", "v2")

    result = _FakeGateResult()
    error = HandoffRejected(result)  # type: ignore[arg-type]

    assert error.result is result
    assert "2 violation" in str(error)


def test_sovereign_research_unavailable_carries_what_a_gate_needs() -> None:
    """The research handler turns this into a human gate from application/, so it has to
    carry the topic and the file the provider looked for rather than leave the handler to
    parse them back out of a message."""
    error = SovereignResearchUnavailable(
        "OAuth device flow", "no evidence", evidence_name="oauthdeviceflow.md"
    )

    assert isinstance(error, VibeyError)
    assert error.topic == "OAuth device flow"
    assert error.detail == "no evidence"
    assert error.evidence_name == "oauthdeviceflow.md"
    assert str(error) == "no evidence"
    assert SovereignResearchUnavailable("?", "unnamed").evidence_name is None


def test_checkout_held_names_the_live_holder_and_its_phase() -> None:
    """`vibey new` on a live project's checkout says who holds it and in which phase, so
    the operator can decide between abandoning that project and choosing another path."""
    holder = UUID(int=7)
    error = CheckoutHeld("/work/triaged-963", holder_id=holder, holder_phase="design")

    assert isinstance(error, VibeyError)
    assert (error.repo_path, error.holder_id, error.holder_phase) == (
        "/work/triaged-963",
        holder,
        "design",
    )
    assert str(error) == (
        f"checkout /work/triaged-963 is held by live project {holder} (phase design); "
        "two live projects never share a checkout, so no project was created"
    )


def test_checkout_held_by_a_holder_since_gone_says_to_run_it_again() -> None:
    """The holder can be abandoned between the refused insert and the read that names it:
    the checkout is free by then, and the message says so instead of naming nobody."""
    error = CheckoutHeld("/work/r", holder_id=None, holder_phase=None)

    assert error.holder_id is None
    assert "has since let it go; run the same command again" in str(error)
    assert "no project was created" in str(error)
