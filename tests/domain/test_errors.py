# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from vibey.domain.errors import (
    BudgetExceeded,
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
