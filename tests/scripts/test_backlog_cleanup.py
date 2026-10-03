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

import subprocess

from scripts import backlog_cleanup as bc


class FakeGh:
    """Answers the loop's reads from fixed text and records every mutation."""

    def __init__(self, comments: str = "", texts: dict[int, tuple[str, str]] | None = None) -> None:
        self._comments = comments
        self._texts = texts or {}
        self.posted: list[tuple[int, str]] = []
        self.duplicates: list[tuple[int, int | None]] = []

    def issue_text(self, number: int) -> tuple[str, str]:
        return self._texts[number]

    def issue_state(self, number: int) -> str:
        return "OPEN"

    def comments(self, number: int) -> str:
        return self._comments

    def comment(self, number: int, body: str) -> bool:
        self.posted.append((number, body))
        return True

    def close(self, number: int, body: str, duplicate_of: int | None = None) -> bool:
        self.posted.append((number, body))
        self.duplicates.append((number, duplicate_of))
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


def _probe(canonical: int, number: int, texts: dict[int, tuple[str, str]]) -> bool:
    gh = FakeGh(texts=texts)
    return bc.DuplicateOfProbe(canonical, number, gh).holds({})  # type: ignore[arg-type]


def test_an_exact_later_copy_is_a_duplicate() -> None:
    same = ("feat(gh): page every listing", "body, byte for byte")
    assert _probe(857, 1002, {857: same, 1002: same})


def test_a_copy_whose_text_drifted_is_not_a_duplicate() -> None:
    texts = {
        857: ("feat(gh): page every listing", "body"),
        1002: ("feat(gh): page every listing", "body, edited"),
    }
    assert not _probe(857, 1002, texts)


def test_the_original_is_never_a_duplicate_of_its_copy() -> None:
    same = ("t", "b")
    assert not _probe(1002, 857, {857: same, 1002: same})


def test_a_done_duplicate_closes_against_the_issue_it_copies() -> None:
    same = ("feat(gh): page every listing", "body")
    gh = FakeGh(texts={857: same, 1002: same})
    expectations = {
        "issues": {
            "1002": {
                "kind": "duplicate",
                "close_when_done": True,
                "probes": [{"duplicate_of": 857}],
            }
        }
    }
    loop = bc.BacklogCleanup(gh, expectations, cutoff="abc123")  # type: ignore[arg-type]
    row = loop._row(1002, same[0], ["qwenstorm"])
    assert row["verdict"] == "DONE"
    counts = loop.apply([row])
    assert counts["closed"] == 1
    assert gh.duplicates == [(1002, 857)]


class RecordingGh(bc.Gh):
    """The real CLI wrapper with the subprocess replaced: records argv, answers per rule."""

    def __init__(self, refuse_duplicate_flag: bool) -> None:
        super().__init__()
        self.refuse = refuse_duplicate_flag
        self.calls: list[tuple[str, ...]] = []

    def _run(self, *args: str, mutation: bool = False) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if self.refuse and "--duplicate-of" in args:
            return subprocess.CompletedProcess(args, 1, "", "unknown flag: --duplicate-of")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_close_marks_the_duplicate_on_the_forge() -> None:
    gh = RecordingGh(refuse_duplicate_flag=False)
    gh.close(1002, "report", 857)
    assert gh.calls == [("issue", "close", "1002", "--comment", "report", "--duplicate-of", "857")]


def test_an_older_gh_closes_the_duplicate_as_not_planned() -> None:
    gh = RecordingGh(refuse_duplicate_flag=True)
    gh.close(1002, "report", 857)
    assert gh.calls[-1] == (
        "issue",
        "close",
        "1002",
        "--comment",
        "report",
        "--reason",
        "not planned",
    )
