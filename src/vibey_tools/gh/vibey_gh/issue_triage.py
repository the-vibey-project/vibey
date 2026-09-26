# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deterministic, repeatable triage and ordering for open GitHub issues.

The forge has no portable issue-order field.  The managed labels below are therefore
the durable order: bumped issues first, then critical/high/medium/low, then oldest
first within a band.  Re-running the sweep derives the same result from the whole
open issue set and never treats issue text as executable input.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from vibey_gh import github_state

TRIAGED = "vibey-gh:triaged"
BUMPED = "vibey-gh:priority-bumped"
PRIORITIES = ("critical", "high", "medium", "low")
PRIORITY_LABELS = tuple(f"vibey-gh:priority-{value}" for value in PRIORITIES)
MANAGED_LABELS = (TRIAGED, BUMPED, *PRIORITY_LABELS)
LABEL_DEFINITIONS = {
    TRIAGED: ("6F42C1", "Issue has been classified by the hourly triage sweep"),
    BUMPED: ("B60205", "Operator-promoted issue; outranks ordinary priority"),
    "vibey-gh:priority-critical": ("B60205", "Highest issue priority"),
    "vibey-gh:priority-high": ("D93F0B", "High issue priority"),
    "vibey-gh:priority-medium": ("FBCA04", "Medium issue priority"),
    "vibey-gh:priority-low": ("C5DEF5", "Low issue priority"),
}


@dataclass(frozen=True)
class RankedIssue:
    number: int
    title: str
    priority: str
    bumped: bool
    created_at: str

    @property
    def rank(self) -> tuple[int, int, str]:
        return (0 if self.bumped else 1, PRIORITIES.index(self.priority), self.created_at)


def _names(issue: dict[str, Any]) -> set[str]:
    return {
        str(x.get("name", "")) if isinstance(x, dict) else str(x) for x in issue.get("labels", [])
    }


def classify(issue: dict[str, Any]) -> str:
    """Classify from explicit severity labels first, then conservative title signals."""
    names = _names(issue)
    for priority in PRIORITIES:
        if f"priority: {priority}" in names or f"vibey-gh:priority-{priority}" in names:
            return priority
    text = f"{issue.get('title', '')} {issue.get('body', '')}".casefold()
    if any(word in text for word in ("security", "data loss", "release blocker", "outage")):
        return "critical"
    if any(word in text for word in ("bug", "broken", "crash", "regression", "failure")):
        return "high"
    if any(word in text for word in ("feature", "support", "add", "improve")):
        return "medium"
    return "low"


def _run(*args: str) -> None:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "GitHub command failed")


def ensure_labels() -> None:
    for name, (colour, description) in LABEL_DEFINITIONS.items():
        _run("label", "create", name, "--color", colour, "--description", description, "--force")


def fetch_open_issues(limit: int = 1000) -> list[dict[str, Any]]:
    value = github_state.gh_json(
        "issue",
        "list",
        "--state",
        "open",
        "--limit",
        str(limit),
        "--json",
        "number,title,body,labels,createdAt,isPullRequest",
    )
    return [
        item for item in value or [] if isinstance(item, dict) and not item.get("isPullRequest")
    ]


def rank(issue: dict[str, Any]) -> RankedIssue:
    return RankedIssue(
        number=int(issue["number"]),
        title=str(issue.get("title") or ""),
        priority=classify(issue),
        bumped=BUMPED in _names(issue),
        created_at=str(issue.get("createdAt") or ""),
    )


def triage(issues: list[dict[str, Any]] | None = None) -> list[RankedIssue]:
    """Reconcile every open issue and return the complete ordered list."""
    ensure_labels()
    ranked = sorted(
        (rank(issue) for issue in (issues if issues is not None else fetch_open_issues())),
        key=lambda x: x.rank,
    )
    for item in ranked:
        desired = [TRIAGED, BUMPED if item.bumped else f"vibey-gh:priority-{item.priority}"]
        args = ["issue", "edit", str(item.number)]
        for label in MANAGED_LABELS:
            if label not in desired:
                args += ["--remove-label", label]
        for label in desired:
            args += ["--add-label", label]
        _run(*args)
    return ranked


def set_bump(issue: int, bumped: bool) -> None:
    """Explicitly promote or remove promotion, then leave ordinary triage to the sweep."""
    ensure_labels()
    args = ["issue", "edit", str(issue)]
    if bumped:
        args += ["--add-label", BUMPED]
    else:
        args += ["--remove-label", BUMPED]
    _run(*args)


def summary(items: list[RankedIssue]) -> str:
    lines = ["### Issue triage order", "", "| Rank | Issue | Priority |", "|---:|---|---|"]
    lines += [
        f"| {i} | #{item.number} {item.title} | {'bumped' if item.bumped else item.priority} |"
        for i, item in enumerate(items, 1)
    ]
    return "\n".join(lines) + "\n"
