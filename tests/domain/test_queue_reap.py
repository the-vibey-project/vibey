# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue reaping: every stuck condition judged by a number against a declared threshold
(ADR-0056). Pure, so the clock is an argument and a property test can drive it."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vibey.domain.interfaces import (
    BrokerPolicyInterface,
    DeadLetterInterface,
    DeadLetterPeekInterface,
    HeldWorkInterface,
    QueueDepthInterface,
    QueueReapPolicyInterface,
    ReapThresholdsInterface,
)
from vibey.domain.queue_reap import (
    QUEUE_REAP_POLICY,
    BrokerPolicy,
    DeadLetter,
    DeadLetterPeek,
    HeldWork,
    HolderState,
    PolicyOutcome,
    QueueDepth,
    ReapAction,
    ReapCondition,
    ReapThresholds,
    ReapVerdict,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
DEFAULTS = ReapThresholds()


def _held(
    *,
    overdue: float = 5.0,
    attempts: int = 1,
    limit: int = 7,
    holder: HolderState = HolderState.UNKNOWN,
    can_dead_letter: bool = False,
) -> HeldWork:
    return HeldWork(
        subject="job-1",
        queue="job:p",
        deadline_at=NOW - timedelta(seconds=overdue),
        attempts=attempts,
        attempt_limit=limit,
        holder=holder,
        can_dead_letter=can_dead_letter,
    )


def _depth(**overrides: object) -> QueueDepth:
    values: dict[str, object] = {
        "queue": "vibey.jobs.p",
        "ready": 0,
        "unacked": 0,
        "consumers": 1,
        "oldest_ready_age_seconds": None,
    }
    values.update(overrides)
    return QueueDepth(**values)  # type: ignore[arg-type]


# -- the seams -------------------------------------------------------------------------


def test_every_value_satisfies_its_interface() -> None:
    assert isinstance(DEFAULTS, ReapThresholdsInterface)
    assert isinstance(_held(), HeldWorkInterface)
    assert isinstance(_depth(), QueueDepthInterface)
    item = DeadLetter(queue="q.dlq", origin_queue="q", reason="rejected", body="{}")
    assert isinstance(item, DeadLetterInterface)
    assert isinstance(DeadLetterPeek(queue="q.dlq", depth=0), DeadLetterPeekInterface)
    assert isinstance(
        BrokerPolicy(name="p", pattern="^v", consumer_timeout_ms=1, delivery_limit=1),
        BrokerPolicyInterface,
    )
    assert isinstance(QUEUE_REAP_POLICY, QueueReapPolicyInterface)


# -- thresholds ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("lease_grace_seconds", -1, "must not be negative"),
        ("stale_ready_seconds", 0, "at least 1"),
        ("dead_letter_min_depth", 0, "at least 1"),
    ],
)
def test_a_threshold_out_of_range_is_refused(field: str, value: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ReapThresholds(**{field: value})  # type: ignore[arg-type]


def test_the_defaults_are_the_declared_ones() -> None:
    assert (
        ReapThresholds(lease_grace_seconds=0, stale_ready_seconds=900, dead_letter_min_depth=1)
        == DEFAULTS
    )


# -- (a), (b), (c): held work ----------------------------------------------------------


def test_work_within_its_deadline_is_not_reaped() -> None:
    assert QUEUE_REAP_POLICY.judge_held(_held(overdue=-1), now=NOW, thresholds=DEFAULTS) is None


def test_work_exactly_at_the_grace_is_not_reaped() -> None:
    thresholds = ReapThresholds(lease_grace_seconds=30)
    assert QUEUE_REAP_POLICY.judge_held(_held(overdue=30), now=NOW, thresholds=thresholds) is None


@pytest.mark.parametrize(
    ("holder", "condition"),
    [
        (HolderState.LIVE, ReapCondition.HUNG_HANDLER),
        (HolderState.GONE, ReapCondition.HOLDER_GONE),
        (HolderState.UNKNOWN, ReapCondition.LEASE_EXPIRED),
    ],
)
def test_overdue_work_with_attempts_left_is_requeued(
    holder: HolderState, condition: ReapCondition
) -> None:
    verdict = QUEUE_REAP_POLICY.judge_held(
        _held(overdue=12.5, holder=holder), now=NOW, thresholds=DEFAULTS
    )
    assert verdict == ReapVerdict(
        subject="job-1",
        queue="job:p",
        condition=condition,
        measured=12.5,
        threshold=0.0,
        unit="seconds past deadline",
        action=ReapAction.REQUEUE,
        detail={"attempts": 1, "attempt_limit": 7},
    )


def test_overdue_work_at_its_limit_is_parked_where_there_is_no_dead_letter_queue() -> None:
    verdict = QUEUE_REAP_POLICY.judge_held(_held(attempts=7, limit=7), now=NOW, thresholds=DEFAULTS)
    assert verdict is not None
    assert verdict.condition is ReapCondition.POISON
    assert verdict.action is ReapAction.PARK
    assert (verdict.measured, verdict.threshold, verdict.unit) == (7.0, 7.0, "attempts")
    assert verdict.detail == {"overdue_seconds": 5.0, "holder": "unknown"}


def test_overdue_work_past_its_limit_is_dead_lettered_where_it_can_be() -> None:
    verdict = QUEUE_REAP_POLICY.judge_held(
        _held(attempts=9, limit=3, can_dead_letter=True), now=NOW, thresholds=DEFAULTS
    )
    assert verdict is not None
    assert verdict.condition is ReapCondition.POISON
    assert verdict.action is ReapAction.DEAD_LETTER


@settings(max_examples=300, deadline=None)
@given(
    overdue=st.floats(min_value=-10_000, max_value=10_000, allow_nan=False),
    grace=st.integers(min_value=0, max_value=600),
    attempts=st.integers(min_value=0, max_value=50),
    limit=st.integers(min_value=1, max_value=50),
    holder=st.sampled_from(list(HolderState)),
    can_dead_letter=st.booleans(),
)
def test_held_work_property(
    overdue: float,
    grace: int,
    attempts: int,
    limit: int,
    holder: HolderState,
    can_dead_letter: bool,
) -> None:
    """The gate is the number, and the ladder is bounded.

    A verdict exists exactly when the work has run past its deadline by more than the
    grace. It never requeues work at or over its limit -- the unbounded ladder ADR-0024
    rules out -- and it always requeues work under it. It always carries a measurement
    over its threshold, and the same inputs always give the same verdict.
    """
    work = _held(
        overdue=overdue,
        attempts=attempts,
        limit=limit,
        holder=holder,
        can_dead_letter=can_dead_letter,
    )
    thresholds = ReapThresholds(lease_grace_seconds=grace)
    verdict = QUEUE_REAP_POLICY.judge_held(work, now=NOW, thresholds=thresholds)
    late = (NOW - work.deadline_at).total_seconds() > grace
    assert (verdict is not None) == late
    if verdict is None:
        return
    assert verdict == QUEUE_REAP_POLICY.judge_held(work, now=NOW, thresholds=thresholds)
    assert verdict.measured >= verdict.threshold
    if attempts >= limit:
        assert verdict.condition is ReapCondition.POISON
        assert verdict.action is not ReapAction.REQUEUE
        assert verdict.action is (ReapAction.DEAD_LETTER if can_dead_letter else ReapAction.PARK)
    else:
        assert verdict.action is ReapAction.REQUEUE
        assert verdict.measured > verdict.threshold


# -- (b), (d), (e): queues -------------------------------------------------------------


def test_a_healthy_queue_yields_nothing() -> None:
    assert QUEUE_REAP_POLICY.judge_queue(_depth(ready=3, consumers=2), thresholds=DEFAULTS) == ()


def test_unacked_messages_with_no_consumer_are_surfaced() -> None:
    (verdict,) = QUEUE_REAP_POLICY.judge_queue(_depth(unacked=4, consumers=0), thresholds=DEFAULTS)
    assert verdict.condition is ReapCondition.HOLDER_GONE
    assert verdict.action is ReapAction.SURFACE
    assert (verdict.measured, verdict.threshold) == (4.0, 0.0)


def test_unacked_messages_with_unknown_consumers_are_not_surfaced() -> None:
    assert (
        QUEUE_REAP_POLICY.judge_queue(_depth(unacked=4, consumers=None), thresholds=DEFAULTS) == ()
    )


def test_old_ready_work_with_no_consumer_is_surfaced() -> None:
    (verdict,) = QUEUE_REAP_POLICY.judge_queue(
        _depth(ready=2, consumers=0, oldest_ready_age_seconds=901.0), thresholds=DEFAULTS
    )
    assert verdict.condition is ReapCondition.STALE_READY
    assert verdict.action is ReapAction.SURFACE
    assert (verdict.measured, verdict.threshold) == (901.0, 900.0)
    assert verdict.detail == {"ready": 2}


def test_old_ready_work_where_consumers_cannot_be_counted_is_surfaced() -> None:
    """PostgreSQL knows no workers; a live one would have claimed the work."""
    (verdict,) = QUEUE_REAP_POLICY.judge_queue(
        _depth(ready=1, consumers=None, oldest_ready_age_seconds=900.0), thresholds=DEFAULTS
    )
    assert verdict.condition is ReapCondition.STALE_READY


@pytest.mark.parametrize(
    "depth",
    [
        _depth(ready=2, consumers=1, oldest_ready_age_seconds=10_000.0),
        _depth(ready=2, consumers=0, oldest_ready_age_seconds=899.0),
        _depth(ready=2, consumers=0, oldest_ready_age_seconds=None),
        _depth(ready=0, consumers=0, oldest_ready_age_seconds=10_000.0),
    ],
)
def test_ready_work_that_is_taken_young_or_unmeasured_is_not_surfaced(depth: QueueDepth) -> None:
    assert QUEUE_REAP_POLICY.judge_queue(depth, thresholds=DEFAULTS) == ()


def test_both_queue_conditions_can_hold_at_once() -> None:
    verdicts = QUEUE_REAP_POLICY.judge_queue(
        _depth(ready=1, unacked=1, consumers=0, oldest_ready_age_seconds=1_000.0),
        thresholds=DEFAULTS,
    )
    assert [v.condition for v in verdicts] == [
        ReapCondition.HOLDER_GONE,
        ReapCondition.STALE_READY,
    ]


def test_an_owned_dead_letter_queue_is_parked_and_a_foreign_one_surfaced() -> None:
    owned = _depth(queue="vibey.x.dlq", ready=2, unacked=1, dead_letter=True, owned=True)
    (verdict,) = QUEUE_REAP_POLICY.judge_queue(owned, thresholds=DEFAULTS)
    assert verdict.condition is ReapCondition.DEAD_LETTERED
    assert verdict.action is ReapAction.PARK
    assert (verdict.measured, verdict.threshold) == (3.0, 1.0)
    foreign = _depth(queue="celery.dlq", ready=1, dead_letter=True, owned=False)
    (verdict,) = QUEUE_REAP_POLICY.judge_queue(foreign, thresholds=DEFAULTS)
    assert verdict.action is ReapAction.SURFACE


def test_a_dead_letter_queue_below_its_depth_is_not_acted_on() -> None:
    thresholds = ReapThresholds(dead_letter_min_depth=5)
    depth = _depth(queue="q.dlq", ready=4, dead_letter=True, owned=True)
    assert QUEUE_REAP_POLICY.judge_queue(depth, thresholds=thresholds) == ()


@settings(max_examples=300, deadline=None)
@given(
    ready=st.integers(min_value=0, max_value=1_000),
    unacked=st.integers(min_value=0, max_value=1_000),
    consumers=st.one_of(st.none(), st.integers(min_value=0, max_value=10)),
    age=st.one_of(st.none(), st.floats(min_value=0, max_value=100_000, allow_nan=False)),
    dead_letter=st.booleans(),
    owned=st.booleans(),
    stale=st.integers(min_value=1, max_value=10_000),
    min_depth=st.integers(min_value=1, max_value=50),
)
def test_queue_property(
    ready: int,
    unacked: int,
    consumers: int | None,
    age: float | None,
    dead_letter: bool,
    owned: bool,
    stale: int,
    min_depth: int,
) -> None:
    """Nothing vibey does not own is ever parked; only a dead-letter queue is ever parked;
    unmeasured is never old; nothing is ever requeued or dead-lettered from a measurement
    of a whole queue; and every verdict's measurement meets its threshold."""
    depth = _depth(
        ready=ready,
        unacked=unacked,
        consumers=consumers,
        oldest_ready_age_seconds=age,
        dead_letter=dead_letter,
        owned=owned,
    )
    thresholds = ReapThresholds(stale_ready_seconds=stale, dead_letter_min_depth=min_depth)
    verdicts = QUEUE_REAP_POLICY.judge_queue(depth, thresholds=thresholds)
    for verdict in verdicts:
        assert verdict.action in (ReapAction.PARK, ReapAction.SURFACE)
        assert verdict.measured >= verdict.threshold
        if verdict.action is ReapAction.PARK:
            assert owned and dead_letter
        if verdict.condition is ReapCondition.STALE_READY:
            assert age is not None and not dead_letter
    if dead_letter:
        assert all(v.condition is ReapCondition.DEAD_LETTERED for v in verdicts)
        assert bool(verdicts) == (ready + unacked >= min_depth)


# -- (e): dead letters -----------------------------------------------------------------


def test_a_dead_letter_is_known_by_its_own_id() -> None:
    item = DeadLetter(queue="q.dlq", origin_queue="q", reason="rejected", body="{}", message_id="m")
    assert item.identity == "id:m"


def test_a_dead_letter_without_an_id_is_known_by_a_digest_of_where_when_and_what() -> None:
    one = DeadLetter(queue="q.dlq", origin_queue="q", reason="r", body="{}", first_death_at="1")
    same = DeadLetter(queue="q.dlq", origin_queue="q", reason="x", body="{}", first_death_at="1")
    later = DeadLetter(queue="q.dlq", origin_queue="q", reason="r", body="{}", first_death_at="2")
    assert one.identity.startswith("sha256:")
    assert one.identity == same.identity
    assert one.identity != later.identity
    assert (
        DeadLetter(queue="q.dlq", origin_queue="q", reason="r", body="{}").identity != one.identity
    )


@pytest.mark.parametrize(
    ("body", "truncated", "expected"),
    [
        ('{"a": 1}', False, {"a": 1}),
        ('{"a": 1}', True, None),
        ("[1]", False, None),
        ("not json", False, None),
    ],
)
def test_only_a_whole_json_object_is_a_payload(
    body: str, truncated: bool, expected: dict[str, object] | None
) -> None:
    item = DeadLetter(queue="q.dlq", origin_queue="q", reason="r", body=body, truncated=truncated)
    assert item.payload_object() == expected


def test_a_dead_letter_is_parked_when_its_queue_is_owned() -> None:
    item = DeadLetter(queue="vibey.q.dlq", origin_queue="vibey.q", reason="expired", body="{}")
    depth = _depth(queue="vibey.q.dlq", ready=3, dead_letter=True, owned=True)
    verdict = QUEUE_REAP_POLICY.judge_dead_letter(item, depth, thresholds=DEFAULTS)
    assert verdict.subject == item.identity
    assert verdict.action is ReapAction.PARK
    assert verdict.detail == {"origin_queue": "vibey.q", "reason": "expired"}
    foreign = QUEUE_REAP_POLICY.judge_dead_letter(
        item, _depth(queue="q.dlq", ready=1, dead_letter=True), thresholds=DEFAULTS
    )
    assert foreign.action is ReapAction.SURFACE


def test_a_whole_read_leaves_nothing_unread() -> None:
    item = DeadLetter(queue="q.dlq", origin_queue="q", reason="r", body="{}")
    peek = DeadLetterPeek(queue="q.dlq", depth=1, items=(item,))
    assert peek.complete
    assert QUEUE_REAP_POLICY.judge_unread(peek) is None


def test_a_partial_read_surfaces_what_it_did_not_reach() -> None:
    item = DeadLetter(queue="q.dlq", origin_queue="q", reason="r", body="{}")
    peek = DeadLetterPeek(queue="q.dlq", depth=5, items=(item,))
    assert not peek.complete
    verdict = QUEUE_REAP_POLICY.judge_unread(peek)
    assert verdict is not None
    assert verdict.action is ReapAction.SURFACE
    assert verdict.condition is ReapCondition.DEAD_LETTERED
    assert (verdict.measured, verdict.threshold) == (4.0, 0.0)
    assert verdict.detail == {"read": 1, "depth": 5}


# -- the broker policy -----------------------------------------------------------------


def _policy(**overrides: object) -> BrokerPolicy:
    values: dict[str, object] = {
        "name": "vibey-reap",
        "pattern": r"^vibey\.",
        "consumer_timeout_ms": 21_600_000,
        "delivery_limit": 20,
    }
    values.update(overrides)
    return BrokerPolicy(**values)  # type: ignore[arg-type]


def test_the_policy_owns_by_its_pattern_and_knows_a_dead_letter_queue() -> None:
    policy = _policy()
    assert policy.owns("vibey.jobs.p")
    assert not policy.owns("celery")
    assert policy.is_dead_letter("vibey.jobs.dead")
    assert policy.is_dead_letter("x.dlq")
    assert not policy.is_dead_letter("vibey.jobs.p")


def test_the_policy_document_is_what_the_management_api_takes() -> None:
    assert _policy(priority=3).body() == {
        "pattern": r"^vibey\.",
        "definition": {"consumer-timeout": 21_600_000, "delivery-limit": 20},
        "priority": 3,
        "apply-to": "queues",
    }


def test_a_policy_read_back_matches_only_itself() -> None:
    policy = _policy()
    assert policy.matches(json.loads(json.dumps(policy.body())))
    assert policy.matches({**policy.body(), "name": "vibey-reap", "vhost": "/"})
    assert not policy.matches(None)
    assert not policy.matches({**policy.body(), "priority": 1})
    assert not policy.matches({**policy.body(), "definition": {}})


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": " "}, "needs a name"),
        ({"pattern": "("}, "pattern is not a regular expression"),
        ({"dead_letter_pattern": "["}, "dead_letter_pattern is not a regular expression"),
        ({"consumer_timeout_ms": 0}, "consumer_timeout_ms"),
        ({"delivery_limit": 0}, "delivery_limit"),
    ],
)
def test_a_malformed_policy_is_refused(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _policy(**overrides)


# -- the ledger payload ----------------------------------------------------------------


def test_a_verdict_payload_names_object_condition_measure_threshold_and_action() -> None:
    verdict = ReapVerdict(
        subject="s",
        queue="q",
        condition=ReapCondition.POISON,
        measured=3.0,
        threshold=3.0,
        unit="attempts",
        action=ReapAction.PARK,
    )
    assert verdict.payload() == {
        "object": "s",
        "queue": "q",
        "condition": "poison",
        "measured": 3.0,
        "threshold": 3.0,
        "unit": "attempts",
        "action": "park",
    }
    detailed = ReapVerdict(
        subject="s",
        queue="q",
        condition=ReapCondition.POISON,
        measured=3.0,
        threshold=3.0,
        unit="attempts",
        action=ReapAction.PARK,
        detail={"k": 1},
    )
    assert detailed.payload()["detail"] == {"k": 1}


def test_a_policy_outcome_says_what_was_read_back() -> None:
    assert PolicyOutcome(policy="p", verified=False).detail == ""
