# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Telling a defect from bad luck (domain/defect.py).

A failure's signature must be the same for two runs of one fault -- whatever ids, times,
durations or counters they carried -- and different for two different faults. The policy
calls a job a defect only when its newest K failures share one signature.
"""

import pytest

from vibey.domain.defect import (
    DEFAULT_IDENTICAL_FAILURES,
    DEFECT_ABANDON,
    DEFECT_ANSWERS,
    DEFECT_OPTIONS,
    DEFECT_REQUEUE,
    EXCERPT_LENGTH,
    FAILURE_NORMALIZER,
    REPEATED_FAILURE_POLICY,
    DefectVerdict,
    FailureSignature,
)
from vibey.domain.interfaces.defect_interface import (
    DefectAnswerPolicyInterface,
    FailureNormalizerInterface,
    RepeatedFailurePolicyInterface,
)
from vibey.domain.job import ATTEMPTS_EXHAUSTED_GATE_KIND, DEFECT_GATE_KIND


def test_the_shared_instances_satisfy_their_declared_seams() -> None:
    assert isinstance(FAILURE_NORMALIZER, FailureNormalizerInterface)
    assert isinstance(REPEATED_FAILURE_POLICY, RepeatedFailurePolicyInterface)
    assert isinstance(DEFECT_ANSWERS, DefectAnswerPolicyInterface)


def test_the_defect_answers_are_requeue_then_abandon() -> None:
    assert DEFECT_OPTIONS == (DEFECT_REQUEUE, DEFECT_ABANDON) == ("requeue", "abandon")
    assert DEFAULT_IDENTICAL_FAILURES == 3


@pytest.mark.parametrize(
    ("detail", "normalized"),
    [
        ("job 3f2a1c9e-1111-2222-3333-444455556666 died", "job <uuid> died"),
        ("at 2026-09-28T12:01:02.345Z it broke", "at <time> it broke"),
        ("at 2026-09-28 12:01 it broke", "at <time> it broke"),
        ("on 2026-09-28 it broke", "on <time> it broke"),
        ("at 12:01:02 it broke", "at <time> it broke"),
        ("object at 0x7f3a9c0b1e50", "object at <addr>"),
        ("wrote /tmp/pytest-of-adam/pytest-12/x.py", "wrote <tmp>"),
        ("wrote /private/var/folders/ab/cd/T/x.py", "wrote <tmp>"),
        ("timed out after 12.5s", "timed out after <duration>"),
        ("timed out after 450 ms", "timed out after <duration>"),
        ("took 3 minutes", "took <duration>"),
        ("on attempt 3 of 7", "on attempt <n>"),
        ("Retry #4 failed", "Retry <n> failed"),
        ("verify round 2/5 failed", "verify round <n> failed"),
        ("head is abcdef1234567", "head is <hex>"),
        ("pid 48213 exited", "pid <n> exited"),
        ("  lots \n of\t  space  ", "lots of space"),
        (
            "AssertionError: expected 3 == 4 at line 42",
            "AssertionError: expected 3 == 4 at line 42",
        ),
    ],
)
def test_the_volatile_parts_of_a_failure_are_normalized_away(detail: str, normalized: str) -> None:
    assert FAILURE_NORMALIZER.normalize(detail) == normalized


def test_two_runs_of_one_fault_share_a_signature() -> None:
    first = FAILURE_NORMALIZER.signature(
        "work",
        "job 3f2a1c9e-1111-2222-3333-444455556666 failed at 2026-09-28T12:01:02Z after "
        "12.5s (attempt 3 of 7): ImportError: no module named greeter",
    )
    second = FAILURE_NORMALIZER.signature(
        "work",
        "job 00000000-aaaa-bbbb-cccc-dddddddddddd failed at 2026-09-29T08:00:00Z after "
        "9s (attempt 4 of 7): ImportError: no module named greeter",
    )
    assert first == second
    assert len(first.digest) == 16


def test_different_faults_and_different_classes_differ() -> None:
    one = FAILURE_NORMALIZER.signature("work", "ImportError: no module named greeter")
    other = FAILURE_NORMALIZER.signature("work", "AssertionError: 3 != 4")
    same_text_other_class = FAILURE_NORMALIZER.signature(
        "engine", "ImportError: no module named greeter"
    )
    assert len({one.digest, other.digest, same_text_other_class.digest}) == 3


def test_a_signature_carries_a_bounded_excerpt_but_hashes_everything() -> None:
    long_head = "x" * EXCERPT_LENGTH
    one = FAILURE_NORMALIZER.signature("work", long_head + " tail one")
    other = FAILURE_NORMALIZER.signature("work", long_head + " tail two")
    assert one.excerpt == other.excerpt == long_head
    assert one.digest != other.digest


def test_a_signature_round_trips_through_its_payload() -> None:
    signature = FAILURE_NORMALIZER.signature("work", "boom")
    assert signature.payload() == {
        "failure_class": "work",
        "signature": signature.digest,
        "excerpt": "boom",
    }
    assert FailureSignature.from_payload(signature.payload()) == signature
    # An excerpt is optional to a reader; the class and digest are not.
    assert FailureSignature.from_payload({"failure_class": "work", "signature": "abc"}) == (
        FailureSignature(failure_class="work", digest="abc", excerpt="")
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"failure_class": "work"},
        {"signature": "abc"},
        {"failure_class": 1, "signature": "abc"},
        {"failure_class": "work", "signature": "abc", "excerpt": 7},
    ],
)
def test_a_payload_no_vibey_wrote_as_a_signature_reads_as_none(payload: dict[str, object]) -> None:
    assert FailureSignature.from_payload(payload) is None


def _sig(digest: str) -> FailureSignature:
    return FailureSignature(failure_class="work", digest=digest, excerpt=digest)


def test_the_newest_failures_all_alike_are_a_defect() -> None:
    recent = [_sig("a"), _sig("a"), _sig("a"), _sig("b")]
    verdict = REPEATED_FAILURE_POLICY.judge(recent, threshold=3)
    assert verdict == DefectVerdict(signature=_sig("a"), identical=3)


def test_the_whole_identical_run_is_counted() -> None:
    verdict = REPEATED_FAILURE_POLICY.judge([_sig("a")] * 5, threshold=2)
    assert verdict is not None
    assert verdict.identical == 5


@pytest.mark.parametrize(
    ("recent", "threshold"),
    [
        ([_sig("a"), _sig("a"), _sig("b")], 3),  # varied: may yet succeed
        ([_sig("a"), _sig("a")], 3),  # too few recorded to say
        ([_sig("a")] * 5, 0),  # switched off
        ([_sig("a")] * 5, 1),  # one failure is always alike itself
        ([], 3),
    ],
)
def test_varied_or_too_few_failures_are_not_a_defect(
    recent: list[FailureSignature], threshold: int
) -> None:
    assert REPEATED_FAILURE_POLICY.judge(recent, threshold=threshold) is None


@pytest.mark.parametrize(
    ("kind", "answer", "abandons"),
    [
        (DEFECT_GATE_KIND, {"choice": "abandon"}, True),
        (DEFECT_GATE_KIND, {"choice": "requeue"}, False),
        (DEFECT_GATE_KIND, {}, False),
        (DEFECT_GATE_KIND, None, False),
        (ATTEMPTS_EXHAUSTED_GATE_KIND, {"choice": "abandon"}, False),
    ],
)
def test_only_an_abandoned_defect_gate_cancels_its_job(
    kind: str, answer: dict[str, object] | None, abandons: bool
) -> None:
    assert DEFECT_ANSWERS.abandons(kind, answer) is abandons
