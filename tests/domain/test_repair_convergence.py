# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""When a repair that changes nothing is a reason to stop repairing."""

from datetime import UTC, datetime, timedelta

import pytest

from vibey.domain.repair_convergence import (
    IDENTICAL_FAILURES_BEFORE_PARKING,
    REPAIR_NOT_CONVERGING_GATE_KIND,
    failure_signature,
    failures_since,
    is_not_converging,
    not_converging_prompt,
)

NEXT_MISSING = (
    "gate failed: npm run build: > Build error occurred\n"
    "Error: Turbopack build failed with 1 error:\n./src/app\n"
    "Error: Could not find the Next.js package (next/package.json)\n"
    "Resolved from: /Users/adam/git/portfolio/.vibey/worktrees/d77e39c4/1/ws/src/app"
)


def test_the_same_failure_in_another_worktree_has_the_same_signature() -> None:
    elsewhere = NEXT_MISSING.replace("/ws/", "/integration/").replace("d77e39c4", "0badf00d")

    assert failure_signature(NEXT_MISSING) == failure_signature(elsewhere)


@pytest.mark.parametrize(
    ("one", "other"),
    [
        ("Test failed at line 12 after 340 ms", "test failed at line 98 after 7 ms"),
        ("commit 3f0112fe9a failed", "commit 9d8c7b6a5e failed"),
        ("error:   too   many\n\nspaces", "ERROR: too many spaces"),
        ("fail C:/work/a/b.ts", "fail D:/other/c.ts"),
    ],
    ids=["numbers", "hex-ids", "whitespace-and-case", "windows-path"],
)
def test_what_changes_between_identical_failures_is_not_part_of_the_signature(
    one: str, other: str
) -> None:
    assert failure_signature(one) == failure_signature(other)


def test_a_different_failure_has_a_different_signature() -> None:
    assert failure_signature(NEXT_MISSING) != failure_signature(
        "gate failed: npm run lint: 3 errors in src/lib/a.ts"
    )


def test_only_the_head_of_a_long_failure_is_compared() -> None:
    head = "build failed: " + "x" * 2_000
    assert failure_signature(head + " tail one") == failure_signature(head + " tail two")


def test_a_failure_with_no_text_has_no_signature() -> None:
    assert failure_signature("   \n ") == ""


def test_what_was_raised_before_a_persons_answer_does_not_count() -> None:
    start = datetime(2026, 10, 11, tzinfo=UTC)
    history = [(start + timedelta(minutes=n), f"failure {n}") for n in range(4)]

    assert failures_since(history, None) == [f"failure {n}" for n in range(4)]
    assert failures_since(history, start + timedelta(minutes=1)) == ["failure 2", "failure 3"]
    assert failures_since(history, start + timedelta(minutes=9)) == []
    # Strictly after: a finding raised at the instant of the answer is not a later one.
    assert failures_since(history, start + timedelta(minutes=3)) == []


def test_a_failure_the_last_two_repairs_left_unchanged_is_not_converging() -> None:
    assert IDENTICAL_FAILURES_BEFORE_PARKING == 2
    assert is_not_converging([NEXT_MISSING, NEXT_MISSING], NEXT_MISSING)
    # Older, different findings before the last two do not matter.
    assert is_not_converging(["something else", NEXT_MISSING, NEXT_MISSING], NEXT_MISSING)


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        ([], NEXT_MISSING),
        ([NEXT_MISSING], NEXT_MISSING),
        ([NEXT_MISSING, "a different failure"], NEXT_MISSING),
        (["a different failure", NEXT_MISSING], NEXT_MISSING),
        ([NEXT_MISSING, NEXT_MISSING], "the failure changed"),
        (["", ""], NEXT_MISSING),
        (["", ""], ""),
        ([NEXT_MISSING, NEXT_MISSING], "  "),
    ],
    ids=[
        "no-history",
        "one-repair-only",
        "the-latest-differs",
        "the-one-before-differs",
        "the-new-failure-changed",
        "empty-history",
        "nothing-to-compare",
        "blank-current",
    ],
)
def test_anything_less_than_two_identical_repairs_keeps_repairing(
    previous: list[str], current: str
) -> None:
    assert not is_not_converging(previous, current)


def test_the_number_of_repeats_can_be_set() -> None:
    assert not is_not_converging([NEXT_MISSING, NEXT_MISSING], NEXT_MISSING, repeats=3)
    assert is_not_converging([NEXT_MISSING] * 3, NEXT_MISSING, repeats=3)


def test_the_gate_says_what_repeated_and_where_to_look() -> None:
    prompt = not_converging_prompt("ws", "verification", 2, NEXT_MISSING)

    assert REPAIR_NOT_CONVERGING_GATE_KIND == "repair_not_converging"
    assert "'ws'" in prompt and "failed verification the same way 3 times running" in prompt
    assert "through 2 repair rounds that changed nothing" in prompt
    assert "Could not find the Next.js package" in prompt  # the failure is quoted
    assert "almost never a code problem" in prompt and "environment" in prompt
    assert "answer anything" in prompt


def test_a_long_failure_is_quoted_only_in_part() -> None:
    assert len(not_converging_prompt("ws", "integration", 2, "e" * 5_000)) < 1_200
