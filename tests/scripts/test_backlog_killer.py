# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/backlog_killer.py` against a fake forge.

What it must never pick (work held for the operator, already in flight, filed by a lane, or a
self-closing tracker), how it ranks what is left, and that the daily rotation is a function of
the date alone -- so the job that dispatches and the agent that works agree on the issue.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from scripts import backlog_killer as bk


def issue(
    number: int, *labels: str, created: str = "2026-09-01T00:00:00Z", **extra: Any
) -> dict[str, Any]:
    return {
        "number": number,
        "title": extra.pop("title", f"issue {number}"),
        "labels": [{"name": name} for name in labels],
        "body": extra.pop("body", "do the thing"),
        "createdAt": created,
        "author": {"login": extra.pop("author", "adammatthewsteinberger")},
    }


class FakeSource:
    def __init__(
        self, issues: list[dict[str, Any]], prs: list[dict[str, Any]] | None = None
    ) -> None:
        self._issues = issues
        self._prs = prs or []

    def open_issues(self) -> list[dict[str, Any]]:
        return self._issues

    def open_pull_requests(self) -> list[dict[str, Any]]:
        return self._prs


SETTINGS: dict[str, Any] = {
    "window": 3,
    "body_chars": 40,
    "priority_labels": ["p:critical", "p:high", "p:low"],
    "skip_labels": ["operator", "qwenstorm"],
    "skip_authors": ["app/github-actions"],
}
EXPECTATIONS: dict[str, Any] = {
    "issues": {"7": {"never_act": True}, "8": {"kind": "triaged"}},
    "self_closing_markers": ["<!-- vibey-gh:tracking:"],
}


def killer(
    issues: list[dict[str, Any]], prs: list[dict[str, Any]] | None = None, **override: Any
) -> bk.BacklogKiller:
    return bk.BacklogKiller(FakeSource(issues, prs), {**SETTINGS, **override}, EXPECTATIONS)


def test_held_in_flight_skipped_machine_filed_and_self_closing_issues_are_never_picked() -> None:
    issues = [
        issue(1),
        issue(2, "operator"),
        issue(3, "qwenstorm"),
        issue(4, author="app/github-actions"),
        issue(5, body="<!-- vibey-gh:tracking:red-branch:develop -->\nred"),
        issue(6),  # named by an open pull request
        issue(7),  # never_act
        issue(8),  # an expectations entry without a hold is still workable
    ]
    prs = [{"number": 900, "title": "fix: the thing", "body": "Refs #6, see also color #ffffff"}]
    assert [i["number"] for i in killer(issues, prs).candidates()] == [1, 8]


def test_a_reference_inside_another_token_is_not_in_flight() -> None:
    prs = [{"number": 900, "title": "x", "body": "https://example.org/page#1 and abc#2"}]
    assert [i["number"] for i in killer([issue(1), issue(2)], prs).candidates()] == [1, 2]


def test_ranked_by_priority_then_age_then_number() -> None:
    issues = [
        issue(10, "p:low", created="2026-01-01T00:00:00Z"),
        issue(11, created="2025-01-01T00:00:00Z"),  # unlabelled: after every tier
        issue(12, "p:high", created="2026-09-02T00:00:00Z"),
        issue(13, "p:high", "p:critical", created="2026-09-03T00:00:00Z"),  # best label wins
        issue(14, "p:high", created="2026-09-01T00:00:00Z"),
        issue(15, "p:high", created="2026-09-01T00:00:00Z"),
    ]
    assert [i["number"] for i in killer(issues).candidates()] == [13, 14, 15, 12, 10, 11]


def test_the_pick_rotates_through_the_window_by_date_and_agrees_with_itself() -> None:
    issues = [issue(n, "p:high", created=f"2026-09-0{n}T00:00:00Z") for n in range(1, 6)]
    k = killer(issues)  # window 3: issues 1, 2, 3
    day = date(2026, 10, 6)
    picks = [k.pick(date.fromordinal(day.toordinal() + i))["number"] for i in range(6)]  # type: ignore[index]
    assert sorted(set(picks)) == [1, 2, 3]
    assert picks[:3] == picks[3:]  # every candidate in the window gets a day, in turn
    assert k.pick(day) == k.pick(day)


def test_a_window_larger_than_the_backlog_rotates_through_what_there_is() -> None:
    k = killer([issue(1), issue(2)], window=10)
    assert {k.pick(date.fromordinal(n))["number"] for n in range(800000, 800004)} == {1, 2}  # type: ignore[index]


def test_nothing_workable_picks_nothing_and_says_so() -> None:
    k = killer([issue(2, "operator")])
    assert k.pick(date(2026, 10, 6)) is None
    assert "No open issue is workable today" in k.brief(None)


def test_the_brief_bounds_the_body_and_says_where_it_was_cut() -> None:
    one = issue(42, "p:high", title="the title", body="x" * 100)
    brief = killer([one]).brief(one)
    assert brief.startswith("Today's backlog item: #42 — the title\nLabels: p:high.")
    assert "gh issue view 42 --comments" in brief
    assert "x" * 40 + "\n\n[cut at 40 characters; read the rest with `gh issue view 42`]" in brief
    assert "x" * 41 not in brief


def test_a_short_body_is_not_cut() -> None:
    one = issue(42, body="short")
    assert "[cut at" not in killer([one]).brief(one)
    assert "Labels: none." in killer([one]).brief(one)


def test_the_declared_settings_load_with_their_expectations() -> None:
    settings, expectations = bk.load(Path(__file__).resolve().parents[2])
    assert settings["prompt"] == "backlog"
    assert "operator" in settings["skip_labels"]
    assert "<!-- vibey-gh:tracking:" in expectations["self_closing_markers"]


def test_missing_expectations_are_no_holds(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/daily_lanes.toml").write_text(
        '[backlog_killer]\nexpectations = "scripts/none.json"\n'
    )
    assert bk.load(tmp_path) == ({"expectations": "scripts/none.json"}, {})


def test_the_cli(monkeypatch, capsys) -> None:
    source = FakeSource([issue(5, "vibey-gh:priority-high", title="five")])
    monkeypatch.setattr(bk, "GhBacklogSource", lambda: source)
    assert bk.main([]) == 2
    assert bk.main(["pick", "--number"]) == 0
    assert capsys.readouterr().out.strip() == "5"
    assert bk.main(["pick"]) == 0
    assert "Today's backlog item: #5 — five" in capsys.readouterr().out
    assert bk.main(["candidates"]) == 0
    assert capsys.readouterr().out.strip() == "#5 five"
    monkeypatch.setattr(bk, "GhBacklogSource", lambda: FakeSource([]))
    assert bk.main(["pick", "--number"]) == 0
    assert capsys.readouterr().out.strip() == ""
