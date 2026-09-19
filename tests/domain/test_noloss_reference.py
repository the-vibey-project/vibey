# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The reference model the no-loss property suite is graded against, and the adversarial
ledgers it is graded on.

The gate (`vibey.domain.noloss`) decides what a brief must carry by calling
`vibey.domain.ledger.open_items`. A property that builds its expected brief with that same
function grades the gate with the gate's own answer key: a bug in `open_items` makes the
expected set wrong in exactly the way the gate is wrong, and every example passes. That is
how the suite stood until #213.

So the model below restates what is still open from the abstract operations a scenario is
made of -- never from `LedgerEvent` payloads, and never through `open_items`, `CLOSES` or
`_ID_FIELD`. It is a different algorithm on purpose: not a replay in seq order that pops,
but "an item is open iff the last event that touches it, by seq, opens it", evaluated in
whatever order the steps arrive. The two can only agree by both being right.

The strategy is what makes 10,000 examples mean something. The suite it replaces drew four
integers from 0..3 -- 256 ledgers in total, all with sequential ids and every event of a
kind contiguous -- so Hypothesis exhausted the space long before any profile's
`max_examples`. Here ids are arbitrary text drawn from one shared pool, so an answer can
name a finding's id, a supersede can name a decision never recorded, and an item can be
reopened after it closed; events of every kind interleave in any order; there are several
verdicts, and the gate receives the ledger in an order unrelated to its seqs.

PROTECTED (`[merge_train] protected_paths`, `.github/CODEOWNERS`): a weaker model or a
narrower strategy silently weakens every property that imports them.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import accumulate
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vibey.domain.handoff import (
    ArtifactRef,
    AssumptionRef,
    DecisionRef,
    HandoffBrief,
    LedgerRef,
    QuestionRef,
    RemainingItem,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event, digest_range
from vibey.domain.noloss import _CONTAINMENT_DENYLIST
from vibey.domain.phase import Phase
from vibey.domain.review import Ambiguity, FindingRef, Severity

pytestmark = pytest.mark.noloss

# The definition of done (docs/plans/implementation-plan.md): "No-loss property suite green
# over 10,000 adversarial examples". Pinned here, in a protected file, because the profile
# itself is registered in tests/conftest.py, which is not -- lowering it there must fail
# this module rather than quietly shrink the suite.
NOLOSS_PROFILE = "noloss"
NOLOSS_EXAMPLES = 10_000

_PROJECT_ID = UUID(int=213)
_CORRELATION_ID = UUID(int=4)
_NOW = datetime(2026, 1, 1, tzinfo=UTC)

# Kinds that must never change what a brief owes. BUDGET_SPENT is excluded on purpose: it is
# R8's input, and these scenarios hold the budget snapshot at zero.
_NOISE = (
    EventKind.SESSION_SEEDED,
    EventKind.TURN_REQUESTED,
    EventKind.TURN_COMPLETED,
    EventKind.TOOL_INVOKED,
    EventKind.FILE_EDITED,
    EventKind.SAVEPOINT_CREATED,
    EventKind.PHASE_TRANSITIONED,
)


def ledger_event(seq: int, kind: EventKind, payload: dict[str, object]) -> LedgerEvent:
    """A ledger event with every field but the ones under test held fixed. Deterministic:
    the ids derive from `seq`, so a replayed Hypothesis example builds the same ledger."""
    return LedgerEvent(
        event_id=UUID(int=seq),
        project_id=_PROJECT_ID,
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=_CORRELATION_ID,
        provenance=Provenance.AGENT,
        produced_at=_NOW,
        payload=payload,
        digest=digest_event(payload),
    )


@dataclass(frozen=True)
class Op:
    """One thing that happened, before it is given a seq.

    `item_id` names the item the operation opens, closes or produces; `supersedes` is the
    decision a DECISION_RECORDED replaces; `remaining` is a verdict's `remaining_work`, and
    `None` omits the key from the payload altogether.
    """

    kind: EventKind
    item_id: str = ""
    supersedes: str | None = None
    text: str = ""
    remaining: tuple[str, ...] | None = None
    referenced: bool = False

    def __post_init__(self) -> None:
        if self.supersedes is not None and self.supersedes == self.item_id:
            # Opened and superseded by the same event at the same seq has no meaning the
            # protocol defines, so the model refuses to have an opinion about it.
            raise ValueError("a decision cannot supersede itself")

    def payload(self) -> dict[str, object]:
        kind = self.kind
        if kind is EventKind.QUESTION_ASKED:
            return {"question_id": self.item_id, "text": self.text, "blocking": False}
        if kind is EventKind.ANSWER_GIVEN:
            return {"question_id": self.item_id, "text": self.text}
        if kind is EventKind.DECISION_RECORDED:
            decided: dict[str, object] = {
                "decision_id": self.item_id,
                "title": self.text,
                "choice": "c",
            }
            if self.supersedes is not None:
                decided["supersedes"] = self.supersedes
            return decided
        if kind is EventKind.ASSUMPTION_STATED:
            return {"assumption_id": self.item_id, "text": self.text, "confidence": "high"}
        if kind is EventKind.FINDING_RAISED:
            return {"finding_id": self.item_id, "severity": "low", "text": self.text}
        if kind is EventKind.FINDING_RESOLVED:
            return {"finding_id": self.item_id, "resolution": "fixed"}
        if kind is EventKind.VERDICT_RENDERED:
            verdict: dict[str, object] = {"complete": not self.remaining}
            if self.remaining is not None:
                verdict["remaining_work"] = list(self.remaining)
            return verdict
        if kind is EventKind.ARTIFACT_PRODUCED:
            return {
                "artifact_id": self.item_id,
                "kind": "file",
                "path": self.text,
                "referenced_by_open_item": self.referenced,
            }
        return {"note": self.text}


@dataclass(frozen=True)
class Scenario:
    """A ledger, as the model sees it (`steps`, in seq order) and as the gate receives it
    (`presented`, the same events in an order unrelated to their seqs)."""

    steps: tuple[tuple[int, Op], ...]
    presented: tuple[LedgerEvent, ...]
    spec_constraints: tuple[str, ...] = ()

    @classmethod
    def of(cls, *ops: Op, spec_constraints: Sequence[str] = ()) -> "Scenario":
        """Hand-written scenarios: seqs 1..n in the order given, presented reversed."""
        steps = tuple(enumerate(ops, start=1))
        events = [ledger_event(seq, op.kind, op.payload()) for seq, op in steps]
        return cls(steps, tuple(reversed(events)), tuple(spec_constraints))

    @property
    def ref(self) -> LedgerRef:
        seqs = [seq for seq, _ in self.steps]
        return LedgerRef(
            uri="handoff/ledger.jsonl",
            from_seq=min(seqs, default=0),
            to_seq=max(seqs, default=0),
            event_count=len(self.presented),
            digest=digest_range(self.presented),
        )


@dataclass(frozen=True)
class Expected:
    """Everything a lossless brief for one scenario must carry, and nothing it may omit."""

    questions: frozenset[str] = frozenset()
    decisions: frozenset[str] = frozenset()
    assumptions: frozenset[str] = frozenset()
    findings: frozenset[str] = frozenset()
    artifacts: frozenset[str] = frozenset()
    remaining: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def without(self, dropped: "Expected") -> "Expected":
        return Expected(
            questions=self.questions - dropped.questions,
            decisions=self.decisions - dropped.decisions,
            assumptions=self.assumptions - dropped.assumptions,
            findings=self.findings - dropped.findings,
            artifacts=self.artifacts - dropped.artifacts,
            remaining=tuple(t for t in self.remaining if t not in dropped.remaining),
            constraints=tuple(c for c in self.constraints if c not in dropped.constraints),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.questions,
                self.decisions,
                self.assumptions,
                self.findings,
                self.artifacts,
                self.remaining,
                self.constraints,
            )
        )


class ReferenceModel:
    """What the handoff protocol says a brief owes, restated without the gate's code.

    - A question is opened by QUESTION_ASKED and closed by ANSWER_GIVEN of the same id.
    - A finding is opened by FINDING_RAISED and closed by FINDING_RESOLVED of the same id.
    - A decision is opened by DECISION_RECORDED and closed by a later DECISION_RECORDED
      whose `supersedes` names it.
    - An assumption, once stated, is never closed.
    - Each kind is its own namespace: an answer never closes a finding that shares its id.
    - An item is open iff the last event touching it, by seq, opened it -- so re-asking a
      question after its answer reopens it, and a supersede that precedes the record it
      names does not close it.
    - Remaining work is the latest verdict's (by seq), each distinct text once; a verdict
      with no `remaining_work` owes nothing.
    - An artifact is owed iff some ARTIFACT_PRODUCED marks it referenced by an open item.
    - Every distinct spec constraint is owed verbatim.
    """

    def expected(self, scenario: Scenario) -> Expected:
        # (namespace, item id) -> (seq, opens?) of the last event, by seq, touching the item.
        last: dict[tuple[str, str], tuple[int, bool]] = {}
        verdict: tuple[int, tuple[str, ...]] | None = None
        artifacts: set[str] = set()
        for seq, op in scenario.steps:
            for namespace, item_id, opens in self._touches(op):
                previous = last.get((namespace, item_id))
                if previous is None or seq > previous[0]:
                    last[(namespace, item_id)] = (seq, opens)
            if op.kind is EventKind.VERDICT_RENDERED and (verdict is None or seq > verdict[0]):
                verdict = (seq, op.remaining or ())
            if op.kind is EventKind.ARTIFACT_PRODUCED and op.referenced:
                artifacts.add(op.item_id)

        def still_open(namespace: str) -> frozenset[str]:
            return frozenset(
                item_id for (ns, item_id), (_, opens) in last.items() if ns == namespace and opens
            )

        return Expected(
            questions=still_open("question"),
            decisions=still_open("decision"),
            assumptions=still_open("assumption"),
            findings=still_open("finding"),
            artifacts=frozenset(artifacts),
            remaining=tuple(dict.fromkeys(verdict[1])) if verdict is not None else (),
            constraints=tuple(dict.fromkeys(scenario.spec_constraints)),
        )

    @staticmethod
    def _touches(op: Op) -> tuple[tuple[str, str, bool], ...]:
        """(namespace, item id, opens?) for every item `op` opens or closes."""
        kind = op.kind
        if kind is EventKind.QUESTION_ASKED:
            return (("question", op.item_id, True),)
        if kind is EventKind.ANSWER_GIVEN:
            return (("question", op.item_id, False),)
        if kind is EventKind.DECISION_RECORDED:
            recorded = ("decision", op.item_id, True)
            if op.supersedes is None:
                return (recorded,)
            return (recorded, ("decision", op.supersedes, False))
        if kind is EventKind.ASSUMPTION_STATED:
            return (("assumption", op.item_id, True),)
        if kind is EventKind.FINDING_RAISED:
            return (("finding", op.item_id, True),)
        if kind is EventKind.FINDING_RESOLVED:
            return (("finding", op.item_id, False),)
        return ()

    @staticmethod
    def brief(expected: Expected) -> HandoffBrief:
        """A brief carrying exactly `expected`, restated in words the gate never reads."""
        return HandoffBrief(
            objective="o",
            constraints=expected.constraints,
            decisions=tuple(DecisionRef(i, "restated") for i in sorted(expected.decisions)),
            assumptions=tuple(AssumptionRef(i, "restated") for i in sorted(expected.assumptions)),
            done=(),
            remaining=tuple(RemainingItem(t) for t in expected.remaining),
            open_questions=tuple(
                QuestionRef(i, "restated", blocking=False) for i in sorted(expected.questions)
            ),
            open_findings=tuple(
                FindingRef(i, Severity.LOW, Ambiguity.CLEAR) for i in sorted(expected.findings)
            ),
            artifacts=tuple(ArtifactRef(i, "restated") for i in sorted(expected.artifacts)),
            invariants=(),
            style_rules=(),
            next_action="keep going",
        )


REFERENCE = ReferenceModel()


# --- The strategy ------------------------------------------------------------------------


def _uncontained(text: str) -> bool:
    """Free text the containment rule (R10) does not flag. R10 is a different property; a
    brief that restates a remaining item verbatim must not fail for spelling "sudo"."""
    lowered = text.lower()
    return not any(phrase in lowered for phrase in _CONTAINMENT_DENYLIST)


TEXT = st.text(max_size=8).filter(_uncontained)
IDS = st.text(max_size=6)

# At most this many distinct ids per scenario. Every kind draws from the SAME pool, so ids
# collide across kinds as well as within one -- the collisions are the point.
POOL_SIZE = 6


@dataclass(frozen=True)
class Shape:
    """An `Op` whose ids are still slots in the scenario's pool.

    The strategies below are module-level constants rather than rebuilt around each drawn
    pool, and text is drawn only where something reads it: a question's, an assumption's
    and a decision's words reach the deterministic brief (and so R10), a verdict's are
    matched verbatim by R1, and an answer's, a finding's or a noise event's never are.
    """

    kind: EventKind
    slot: int = 0
    supersedes: int | None = None
    text: str = ""
    remaining: tuple[str, ...] | None = None
    referenced: bool = False

    def resolve(self, pool: Sequence[str]) -> Op:
        item_id = pool[self.slot % len(pool)]
        supersedes = None if self.supersedes is None else pool[self.supersedes % len(pool)]
        return Op(
            kind=self.kind,
            item_id=item_id,
            # A supersede that lands on its own record is dropped rather than drawn again:
            # see Op.__post_init__.
            supersedes=None if supersedes == item_id else supersedes,
            text=self.text,
            remaining=self.remaining,
            referenced=self.referenced,
        )


_SLOT = st.integers(0, POOL_SIZE - 1)


def _shape(kind: EventKind, **fields: st.SearchStrategy[object]) -> st.SearchStrategy[Shape]:
    return st.builds(Shape, kind=st.just(kind), slot=_SLOT, **fields)


SHAPES: st.SearchStrategy[Shape] = st.one_of(
    _shape(EventKind.QUESTION_ASKED, text=TEXT),
    _shape(EventKind.ANSWER_GIVEN),
    _shape(EventKind.DECISION_RECORDED, supersedes=st.none() | _SLOT, text=TEXT),
    _shape(EventKind.ASSUMPTION_STATED, text=TEXT),
    _shape(EventKind.FINDING_RAISED),
    _shape(EventKind.FINDING_RESOLVED),
    st.builds(
        Shape,
        kind=st.just(EventKind.VERDICT_RENDERED),
        remaining=st.none() | st.lists(TEXT, max_size=4).map(tuple),
    ),
    _shape(EventKind.ARTIFACT_PRODUCED, referenced=st.booleans()),
    st.builds(Shape, kind=st.sampled_from(_NOISE)),
)


@st.composite
def scenarios(draw: st.DrawFn) -> Scenario:
    """Arbitrary ids from one shared pool, every kind interleaved, several verdicts, gapped
    seqs, and a presentation order unrelated to seq."""
    pool = draw(st.lists(IDS, min_size=1, max_size=POOL_SIZE, unique=True))
    ops = [shape.resolve(pool) for shape in draw(st.lists(SHAPES, max_size=30))]
    # Strictly increasing and gapped, built from gaps rather than filtered for uniqueness.
    gaps = draw(st.lists(st.integers(1, 1_000), min_size=len(ops), max_size=len(ops)))
    seqs = list(accumulate(gaps))
    interleaved = draw(st.permutations(ops))
    steps = tuple(zip(seqs, interleaved, strict=True))
    events = [ledger_event(seq, op.kind, op.payload()) for seq, op in steps]
    presented = tuple(draw(st.permutations(events)))
    constraints = tuple(draw(st.lists(TEXT, max_size=4)))
    return Scenario(steps, presented, constraints)


def subset(data: st.DataObject, items: Iterable[str]) -> frozenset[str]:
    """A drawn subset. Sorted first: a frozenset's iteration order is hash-seeded per
    process, so drawing a mask over it would replay against different items."""
    ordered = sorted(items)
    mask = data.draw(st.lists(st.booleans(), min_size=len(ordered), max_size=len(ordered)))
    return frozenset(item for item, drop in zip(ordered, mask, strict=True) if drop)


def dropped_from(data: st.DataObject, expected: Expected) -> Expected:
    """A random part of `expected`, possibly empty, possibly all of it."""
    remaining = subset(data, expected.remaining)
    constraints = subset(data, expected.constraints)
    return Expected(
        questions=subset(data, expected.questions),
        decisions=subset(data, expected.decisions),
        assumptions=subset(data, expected.assumptions),
        findings=subset(data, expected.findings),
        artifacts=subset(data, expected.artifacts),
        remaining=tuple(t for t in expected.remaining if t in remaining),
        constraints=tuple(c for c in expected.constraints if c in constraints),
    )


# --- The model, checked by hand -----------------------------------------------------------


def test_an_answered_question_is_closed_and_a_reasked_one_reopens() -> None:
    answered = Scenario.of(
        Op(EventKind.QUESTION_ASKED, "q"),
        Op(EventKind.ANSWER_GIVEN, "q"),
    )
    reasked = Scenario.of(
        Op(EventKind.QUESTION_ASKED, "q"),
        Op(EventKind.ANSWER_GIVEN, "q"),
        Op(EventKind.QUESTION_ASKED, "q"),
    )
    assert REFERENCE.expected(answered).questions == frozenset()
    assert REFERENCE.expected(reasked).questions == {"q"}


def test_a_supersede_closes_only_what_was_recorded_before_it() -> None:
    scenario = Scenario.of(
        Op(EventKind.DECISION_RECORDED, "old"),
        Op(EventKind.DECISION_RECORDED, "new", supersedes="old"),
        Op(EventKind.DECISION_RECORDED, "early", supersedes="late"),
        Op(EventKind.DECISION_RECORDED, "late"),
    )
    assert REFERENCE.expected(scenario).decisions == {"new", "early", "late"}


def test_a_decision_reinstated_after_its_supersede_is_open_again() -> None:
    scenario = Scenario.of(
        Op(EventKind.DECISION_RECORDED, "d1"),
        Op(EventKind.DECISION_RECORDED, "d2", supersedes="d1"),
        Op(EventKind.DECISION_RECORDED, "d1"),
    )
    assert REFERENCE.expected(scenario).decisions == {"d1", "d2"}


def test_a_decision_cannot_supersede_itself() -> None:
    with pytest.raises(ValueError, match="supersede itself"):
        Op(EventKind.DECISION_RECORDED, "d", supersedes="d")


def test_each_kind_is_its_own_namespace() -> None:
    scenario = Scenario.of(
        Op(EventKind.FINDING_RAISED, "x"),
        Op(EventKind.ANSWER_GIVEN, "x"),
        Op(EventKind.ASSUMPTION_STATED, "x"),
        Op(EventKind.FINDING_RESOLVED, "never-raised"),
    )
    expected = REFERENCE.expected(scenario)
    assert expected.findings == {"x"}
    assert expected.assumptions == {"x"}
    assert expected.questions == frozenset()


def test_only_the_latest_verdict_by_seq_owes_remaining_work() -> None:
    scenario = Scenario.of(
        Op(EventKind.VERDICT_RENDERED, remaining=("stale",)),
        Op(EventKind.VERDICT_RENDERED, remaining=("fresh", "fresh", "also")),
    )
    silent = Scenario.of(
        Op(EventKind.VERDICT_RENDERED, remaining=("stale",)),
        Op(EventKind.VERDICT_RENDERED),
    )
    assert REFERENCE.expected(scenario).remaining == ("fresh", "also")
    assert REFERENCE.expected(silent).remaining == ()


def test_only_a_referenced_artifact_is_owed_and_noise_owes_nothing() -> None:
    scenario = Scenario.of(
        Op(EventKind.ARTIFACT_PRODUCED, "kept", referenced=True),
        Op(EventKind.ARTIFACT_PRODUCED, "loose", referenced=False),
        Op(EventKind.TOOL_INVOKED, text="noise"),
        spec_constraints=("offline", "offline"),
    )
    expected = REFERENCE.expected(scenario)
    assert expected.artifacts == {"kept"}
    assert expected.constraints == ("offline",)
    assert Scenario.of().ref.event_count == 0
    assert REFERENCE.expected(Scenario.of()).is_empty()


def test_containment_filter_rejects_every_denylisted_phrase_in_any_case() -> None:
    assert all(not _uncontained(phrase.upper()) for phrase in _CONTAINMENT_DENYLIST)
    assert _uncontained("wire the retry policy")


# --- The model, checked against the gate's projection --------------------------------------


@given(scenario=scenarios())
def test_the_reference_model_agrees_with_the_ledger_projection(scenario: Scenario) -> None:
    """A differential check: two independently written definitions of "still open". The
    gate is then graded by the model, never by `open_items` itself."""
    from vibey.domain.ledger import open_items

    expected = REFERENCE.expected(scenario)
    projected = {
        "questions": frozenset(open_items(scenario.presented, EventKind.QUESTION_ASKED)),
        "decisions": frozenset(open_items(scenario.presented, EventKind.DECISION_RECORDED)),
        "assumptions": frozenset(open_items(scenario.presented, EventKind.ASSUMPTION_STATED)),
        "findings": frozenset(open_items(scenario.presented, EventKind.FINDING_RAISED)),
    }
    modelled = {
        "questions": expected.questions,
        "decisions": expected.decisions,
        "assumptions": expected.assumptions,
        "findings": expected.findings,
    }
    assert projected == modelled


# --- The dial -------------------------------------------------------------------------------


def test_the_noloss_profile_is_the_definition_of_done() -> None:
    profile = settings.get_profile(NOLOSS_PROFILE)
    assert profile.max_examples == NOLOSS_EXAMPLES
    assert profile.deadline is None


def test_the_noloss_lane_runs_under_the_noloss_profile(request: pytest.FixtureRequest) -> None:
    """`pytest -m noloss` is the CI lane; without `--hypothesis-profile=noloss` it would run
    the default 100 examples and still report green."""
    if request.config.getoption("markexpr") == NOLOSS_PROFILE:
        assert settings.default.max_examples >= NOLOSS_EXAMPLES
