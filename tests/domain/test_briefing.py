# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from hypothesis import given

from tests.domain.test_noloss_reference import REFERENCE, Scenario, scenarios
from vibey.domain.briefing import build_deterministic_brief
from vibey.domain.handoff import BudgetSnapshot, LedgerRef, QuestionRef
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event, digest_range
from vibey.domain.noloss import verify
from vibey.domain.phase import Phase

# Part of the no-loss property suite: protected (`[merge_train] protected_paths`,
# .github/CODEOWNERS), and run alone at 10,000 examples by CI's no-loss lane.
pytestmark = pytest.mark.noloss

PROJECT_ID = uuid4()
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _event(seq: int, kind: EventKind, payload: dict[str, object]) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=PROJECT_ID,
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload=payload,
        digest=digest_event(payload),
    )


def _ref_for(events: list[LedgerEvent]) -> LedgerRef:
    if not events:
        return LedgerRef(uri="u", from_seq=0, to_seq=0, event_count=0, digest=digest_range(()))
    return LedgerRef(
        uri="u",
        from_seq=min(e.seq for e in events),
        to_seq=max(e.seq for e in events),
        event_count=len(events),
        digest=digest_range(events),
    )


ZERO_BUDGET = BudgetSnapshot(turns_spent=0, dollars_spent=0.0, max_turns=None, max_dollars=None)


def test_empty_ledger_produces_a_passing_brief() -> None:
    brief = build_deterministic_brief([])
    result = verify(ledger=[], brief=brief, ref=_ref_for([]), budget=ZERO_BUDGET)
    assert result.ok


def test_open_question_is_carried_verbatim_by_id() -> None:
    events = [
        _event(
            1, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "capped?", "blocking": True}
        )
    ]
    brief = build_deterministic_brief(events)

    assert brief.open_questions == (QuestionRef("q1", "capped?", blocking=True),)
    result = verify(ledger=events, brief=brief, ref=_ref_for(events), budget=ZERO_BUDGET)
    assert result.ok


def test_answered_question_is_not_carried() -> None:
    events = [
        _event(1, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "?", "blocking": False}),
        _event(2, EventKind.ANSWER_GIVEN, {"question_id": "q1", "text": "yes"}),
    ]
    brief = build_deterministic_brief(events)
    assert brief.open_questions == ()


def test_superseded_decision_is_not_carried_but_current_one_is() -> None:
    events = [
        _event(
            1, EventKind.DECISION_RECORDED, {"decision_id": "d1", "title": "old", "choice": "a"}
        ),
        _event(
            2,
            EventKind.DECISION_RECORDED,
            {"decision_id": "d2", "title": "new", "choice": "b", "supersedes": "d1"},
        ),
    ]
    brief = build_deterministic_brief(events)
    ids = {d.decision_id for d in brief.decisions}
    assert ids == {"d2"}


def test_a_decision_recorded_after_the_supersede_naming_it_is_carried() -> None:
    """Found by the widened no-loss strategy (#213): the floor used to consult the
    decision log's `superseded_by`, which ignores order, and dropped a decision the gate
    still counted open -- so the lossless floor failed its own gate."""
    events = [
        _event(
            1,
            EventKind.DECISION_RECORDED,
            {"decision_id": "early", "title": "t", "choice": "a", "supersedes": "late"},
        ),
        _event(
            2, EventKind.DECISION_RECORDED, {"decision_id": "late", "title": "t", "choice": "b"}
        ),
    ]
    brief = build_deterministic_brief(events)
    assert {d.decision_id for d in brief.decisions} == {"early", "late"}
    assert verify(ledger=events, brief=brief, ref=_ref_for(events), budget=ZERO_BUDGET).ok


def test_a_reinstated_decision_is_carried_with_its_latest_wording() -> None:
    events = [
        _event(1, EventKind.DECISION_RECORDED, {"decision_id": "d1", "title": "v1", "choice": "a"}),
        _event(
            2,
            EventKind.DECISION_RECORDED,
            {"decision_id": "d2", "title": "", "choice": "b", "supersedes": "d1"},
        ),
        _event(3, EventKind.DECISION_RECORDED, {"decision_id": "d1", "title": "v2", "choice": "a"}),
    ]
    brief = build_deterministic_brief(events)
    assert {(d.decision_id, d.restatement) for d in brief.decisions} == {("d1", "v2"), ("d2", "b")}
    assert verify(ledger=events, brief=brief, ref=_ref_for(events), budget=ZERO_BUDGET).ok


def test_remaining_work_from_latest_verdict_is_carried() -> None:
    events = [
        _event(1, EventKind.VERDICT_RENDERED, {"complete": False, "remaining_work": ["stale"]}),
        _event(2, EventKind.VERDICT_RENDERED, {"complete": False, "remaining_work": ["fresh"]}),
    ]
    brief = build_deterministic_brief(events)
    assert [r.text for r in brief.remaining] == ["fresh"]
    assert brief.next_action == "fresh"


def test_next_action_defaults_when_nothing_remaining() -> None:
    brief = build_deterministic_brief([])
    assert brief.next_action == "Review and accept."


def test_referenced_artifact_is_carried_unreferenced_is_not() -> None:
    events = [
        _event(
            1,
            EventKind.ARTIFACT_PRODUCED,
            {"artifact_id": "art1", "path": "x.sql", "referenced_by_open_item": True},
        ),
        _event(
            2,
            EventKind.ARTIFACT_PRODUCED,
            {"artifact_id": "art2", "path": "y.sql", "referenced_by_open_item": False},
        ),
    ]
    brief = build_deterministic_brief(events)
    ids = {a.artifact_id for a in brief.artifacts}
    assert ids == {"art1"}


def test_spec_constraints_are_carried_verbatim() -> None:
    brief = build_deterministic_brief([], spec_constraints=("must work offline",))
    assert brief.constraints == ("must work offline",)


def test_finding_with_unknown_severity_falls_back_to_low() -> None:
    events = [
        _event(
            1, EventKind.FINDING_RAISED, {"finding_id": "f1", "severity": "nonsense", "text": "x"}
        )
    ]
    brief = build_deterministic_brief(events)
    assert brief.open_findings[0].severity.value == "low"


def test_finding_with_unknown_ambiguity_falls_back_to_clear() -> None:
    events = [
        _event(
            1,
            EventKind.FINDING_RAISED,
            {"finding_id": "f1", "severity": "high", "text": "x", "ambiguity": "nonsense"},
        )
    ]
    brief = build_deterministic_brief(events)
    assert brief.open_findings[0].ambiguity.value == "clear"


# --- The property that matters: the floor is provably lossless --------------
#
# Graded by the reference model in tests/domain/test_noloss_reference.py, over its
# adversarial ledgers: arbitrary ids, every kind interleaved, closing events and
# supersedes, several verdicts, and a presentation order unrelated to seq.


@given(scenario=scenarios())
def test_deterministic_brief_always_passes_the_gate(scenario: Scenario) -> None:
    brief = build_deterministic_brief(
        scenario.presented, spec_constraints=scenario.spec_constraints
    )
    result = verify(
        ledger=scenario.presented,
        brief=brief,
        ref=scenario.ref,
        budget=ZERO_BUDGET,
        spec_constraints=scenario.spec_constraints,
    )
    assert result.ok, result.violations


@given(scenario=scenarios())
def test_deterministic_brief_carries_exactly_what_is_owed(scenario: Scenario) -> None:
    """Lossless, and not padded: the floor carries every open item and no closed one, so a
    receiving engine is never told to resume work the ledger already settled."""
    expected = REFERENCE.expected(scenario)
    brief = build_deterministic_brief(
        scenario.presented, spec_constraints=scenario.spec_constraints
    )

    assert {q.question_id for q in brief.open_questions} == expected.questions
    assert {d.decision_id for d in brief.decisions} == expected.decisions
    assert {a.assumption_id for a in brief.assumptions} == expected.assumptions
    assert {f.finding_id for f in brief.open_findings} == expected.findings
    assert {a.artifact_id for a in brief.artifacts} == expected.artifacts
    assert set(r.text for r in brief.remaining) == set(expected.remaining)
