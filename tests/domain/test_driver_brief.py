# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver's brief and its no-loss gate (ADR-0070)."""

from dataclasses import replace

from vibey.domain.driver_brief import (
    DRIVER_BRIEF_RENDERER,
    DRIVER_GATE,
    DriverBrief,
    DriverDirection,
)
from vibey.domain.handoff import GateMode, GateRule
from vibey.domain.interfaces.driver_brief_interface import (
    DriverBriefRendererInterface,
    DriverGateInterface,
)

BRIEF = DriverBrief(
    direction=DriverDirection.FAILOVER,
    session_id="abc123",
    cwd="/work/tree",
    transcript_path="/t.jsonl",
    transcript_digest="d1",
    transcript_lines=4,
    branch="feat/x",
    head_sha="cafe",
    dirty_paths=("a.py",),
    next_action="carry on",
    cause="credits",
    target="gptossloop",
    effort="ULTRA",
)


def test_singletons_satisfy_interfaces() -> None:
    assert isinstance(DRIVER_GATE, DriverGateInterface)
    assert isinstance(DRIVER_BRIEF_RENDERER, DriverBriefRendererInterface)


def test_a_complete_brief_passes_strict() -> None:
    result = DRIVER_GATE.verify(BRIEF, digest_now="d1", mode=GateMode.STRICT, attempts=1)
    assert result.ok and result.mode is GateMode.STRICT and result.attempts == 1
    assert result.rules_run == DRIVER_GATE.RULES


def test_every_rule_can_fail() -> None:
    broken = replace(BRIEF, next_action=" ", head_sha="", session_id="", cwd="rel")
    result = DRIVER_GATE.verify(broken, digest_now="other", mode=GateMode.STRICT, attempts=2)
    assert not result.ok
    assert {v.rule for v in result.violations} == {
        GateRule.R1_REMAINING,
        GateRule.R6_RANGE,
        GateRule.R7_ARTIFACTS,
        GateRule.R10_CONTAINMENT,
    }


def test_an_unreadable_transcript_fails_the_range() -> None:
    result = DRIVER_GATE.verify(BRIEF, digest_now=None, mode=GateMode.STRICT, attempts=1)
    assert [v.detail for v in result.violations] == ["transcript unreadable"]


def test_full_transcript_mode_needs_a_copy() -> None:
    result = DRIVER_GATE.verify(BRIEF, digest_now="d1", mode=GateMode.FULL_TRANSCRIPT, attempts=4)
    assert [v.detail for v in result.violations] == ["full-transcript mode names no copy"]
    copied = replace(BRIEF, transcript_copy="/w/.vibey/driver/c.jsonl")
    assert DRIVER_GATE.verify(copied, digest_now="d1", mode=GateMode.FULL_TRANSCRIPT, attempts=4).ok


def test_the_failover_brief_names_the_whole_transcript() -> None:
    text = DRIVER_BRIEF_RENDERER.render(replace(BRIEF, last_message="API Error: limit"))
    assert "`/t.jsonl` (4 lines, sha256 `d1`)" in text
    assert "- `a.py`" in text
    assert "API Error: limit" in text
    assert "Commits made" not in text
    assert text.endswith("carry on\n")


def test_the_handback_brief_lists_commits_and_prefers_the_copy() -> None:
    back = replace(
        BRIEF,
        direction=DriverDirection.HANDBACK,
        dirty_paths=(),
        transcript_copy="/copy.jsonl",
        commits_since=("abc feat: x",),
    )
    text = DRIVER_BRIEF_RENDERER.render(back)
    assert "`/copy.jsonl`" in text and "- (none)" in text and "- abc feat: x" in text
    empty = DRIVER_BRIEF_RENDERER.render(replace(back, commits_since=()))
    assert empty.count("- (none)") == 2
