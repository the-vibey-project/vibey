# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vibey.domain.circuit import UnrecognizedCircuitState
from vibey.domain.engine import EngineId, UnrecognizedEngineId
from vibey.domain.job import UnrecognizedJobState
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedProvenance,
    open_items,
)
from vibey.domain.phase import (
    Denied,
    Phase,
    PhaseState,
    TransitionRequest,
    UnrecognizedPhase,
    evaluate_transition,
)
from vibey.domain.projections import answer_why_question, build_deltas
from vibey.domain.stored_value import StoredValueParser

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def test_unrecognized_value_refuses_known_members() -> None:
    with pytest.raises(ValueError, match="is a known value"):
        UnrecognizedEngineId("claudeloop")

    with pytest.raises(ValueError, match="is a known value"):
        UnrecognizedPhase("build")

    with pytest.raises(ValueError, match="is a known value"):
        UnrecognizedProvenance("trusted")

    with pytest.raises(ValueError, match="is a known value"):
        UnrecognizedJobState("ready")

    with pytest.raises(ValueError, match="is a known value"):
        UnrecognizedCircuitState("closed")


def test_unrecognized_value_string_and_formatting() -> None:
    unknown = UnrecognizedEngineId("ollama-future")
    assert str(unknown) == "ollama-future"
    assert f"{unknown:<15}" == "ollama-future  "


def test_stored_value_parser_known_and_parse() -> None:
    parser = StoredValueParser(EngineId, UnrecognizedEngineId)
    assert parser.known("claudeloop") is EngineId.CLAUDELOOP
    assert parser.known("unknown-engine") is None
    assert parser.parse("claudeloop") is EngineId.CLAUDELOOP
    parsed_unknown = parser.parse("unknown-engine")
    assert isinstance(parsed_unknown, UnrecognizedEngineId)
    assert parsed_unknown.value == "unknown-engine"


def test_evaluate_transition_denied_on_unrecognized_phase() -> None:
    state = PhaseState(
        phase=UnrecognizedPhase("quantum-phase"),
        cycle=1,
        max_cycles=3,
        entered_at=NOW,
    )
    outcome = evaluate_transition(
        state,
        TransitionRequest(to=Phase.BUILD, reason="start build", evidence=()),
    )
    assert isinstance(outcome, Denied)
    assert "is not a phase this vibey knows" in outcome.violations[0]


def test_open_items_and_projections_skip_uninterpretable_events() -> None:
    uninterpretable_phase_event = LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=UnrecognizedPhase("future-phase"),
        seq=1,
        kind=EventKind.QUESTION_ASKED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload={"question_id": "q1", "text": "future question?"},
        digest="digest-1",
    )
    assert not uninterpretable_phase_event.interpretable

    uninterpretable_prov_event = LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=Phase.BUILD,
        seq=2,
        kind=EventKind.FINDING_RAISED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=UnrecognizedProvenance("alien-trust"),
        produced_at=NOW,
        payload={"finding_id": "f1", "text": "alien finding"},
        digest="digest-2",
    )
    assert not uninterpretable_prov_event.interpretable

    events = [uninterpretable_phase_event, uninterpretable_prov_event]

    # open_items skips uninterpretable
    items = open_items(events, EventKind.QUESTION_ASKED)
    assert len(items) == 0

    # build_deltas skips uninterpretable
    deltas = build_deltas(events)
    assert len(deltas.findings) == 0

    why = answer_why_question(events, "why question?")
    assert "No decisions or assumptions recorded" in why
