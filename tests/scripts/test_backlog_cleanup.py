# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/backlog_cleanup.py`'s idempotency guard, against a fake forge.

The loop may touch an issue only when its verdict changed. When the expectations file
has not caught up (the publish job lands it through a branch, not straight onto
develop), the comment marker is the guard that holds -- and it must read the newest
marker, not the oldest, or an unchanged verdict is re-posted every hour.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
# The workflow runs `python scripts/backlog_cleanup.py`, which puts scripts/ on the path
# for its `from interfaces...` import; the test reproduces that before importing.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import backlog_cleanup as bc  # noqa: E402


class FakeGh:
    """Answers the loop's reads from fixed text and records every mutation."""

    def __init__(self, comments: str) -> None:
        self._comments = comments
        self.posted: list[tuple[int, str]] = []

    def issue_state(self, number: int) -> str:
        return "OPEN"

    def comments(self, number: int) -> str:
        return self._comments

    def comment(self, number: int, body: str) -> bool:
        self.posted.append((number, body))
        return True

    def close(self, number: int, body: str) -> bool:
        self.posted.append((number, body))
        return True


def _report(verdict: str, evidence: str) -> str:
    return f"## Status report\n\n**Verdict: {verdict}.**\n\n{bc.marker_for(verdict, evidence)}"


def _row(verdict: str, evidence: str) -> dict[str, object]:
    return {
        "number": 1204,
        "title": "hybrid multiplexer",
        "verdict": verdict,
        "evidence": evidence,
        "missing": "",
        "next": "",
        "act": True,
        "entry": True,
    }


def _loop(gh: FakeGh) -> bc.BacklogCleanup:
    # An entry whose last_verdict was never published: the marker is the only guard.
    expectations = {"issues": {"1204": {"kind": "triaged", "probes": []}}}
    return bc.BacklogCleanup(gh, expectations, cutoff="abc123")  # type: ignore[arg-type]


def test_marker_in_reads_the_newest_marker() -> None:
    text = _report("NEEDS-TRIAGE", "no entry") + "\n" + _report("OPEN", "no probe holds")
    assert bc.marker_in(text) == bc.verdict_hash("OPEN", "no probe holds")


def test_marker_in_without_a_marker_is_none() -> None:
    assert bc.marker_in("a human comment, no marker") is None


def test_an_unchanged_verdict_is_not_reposted_after_an_earlier_one() -> None:
    gh = FakeGh(_report("NEEDS-TRIAGE", "no entry") + "\n" + _report("OPEN", "no probe holds"))
    counts = _loop(gh).apply([_row("OPEN", "no probe holds")])
    assert gh.posted == []
    assert counts["unchanged"] == 1


def test_a_changed_verdict_is_posted_once() -> None:
    gh = FakeGh(_report("OPEN", "no probe holds"))
    counts = _loop(gh).apply([_row("PARTIAL", "grep_hit:x")])
    assert len(gh.posted) == 1
    assert counts["commented"] == 1
    assert bc.marker_in(gh.posted[0][1]) == bc.verdict_hash("PARTIAL", "grep_hit:x")
