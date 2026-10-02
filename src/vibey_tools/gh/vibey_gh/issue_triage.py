# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deterministic, repeatable triage and ordering for open GitHub issues.

The forge has no portable issue-order field.  The managed labels below are therefore
the durable order: bumped issues first, then critical/high/medium/low, then oldest
first within a band.  Re-running the sweep derives the same result from the whole
open issue set and never treats issue text as executable input.

Every call goes through one `GhTransportInterface`. The CLI hands in one that retries a
transient forge failure (`[forge_retry]`, `vibey_gh.gh_retry`): each call here is a read, a
`label create --force` or a label edit, so asking again changes nothing that the first
attempt did not. A sweep failed twice in a day on a single 504 or GraphQL error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface

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


# Module-level, like every function here (vibey ADR-0016): the triage is a facade that the
# CLI and the tests call by name, and it moves onto a class with the rest of the module.
def _run(*args: str, transport: GhTransportInterface | None = None) -> None:
    result = (transport or GhTransport()).run(args)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "GitHub command failed")


def ensure_labels(transport: GhTransportInterface | None = None) -> None:
    for name, (colour, description) in LABEL_DEFINITIONS.items():
        _run(
            "label",
            "create",
            name,
            "--color",
            colour,
            "--description",
            description,
            "--force",
            transport=transport,
        )


def fetch_open_issues(
    limit: int = 1000, transport: GhTransportInterface | None = None
) -> list[dict[str, Any]]:
    value = (transport or GhTransport()).json(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,body,labels,createdAt",
        ]
    )
    return [item for item in value or [] if isinstance(item, dict)]


def rank(issue: dict[str, Any]) -> RankedIssue:
    return RankedIssue(
        number=int(issue["number"]),
        title=str(issue.get("title") or ""),
        priority=classify(issue),
        bumped=BUMPED in _names(issue),
        created_at=str(issue.get("createdAt") or ""),
    )


def triage(
    issues: list[dict[str, Any]] | None = None, transport: GhTransportInterface | None = None
) -> list[RankedIssue]:
    """Reconcile every open issue and return the complete ordered list."""
    ensure_labels(transport)
    if issues is None:
        issues = fetch_open_issues(transport=transport)
    ranked = sorted((rank(issue) for issue in issues), key=lambda x: x.rank)
    for item in ranked:
        desired = [TRIAGED, BUMPED if item.bumped else f"vibey-gh:priority-{item.priority}"]
        args = ["issue", "edit", str(item.number)]
        for label in MANAGED_LABELS:
            if label not in desired:
                args += ["--remove-label", label]
        for label in desired:
            args += ["--add-label", label]
        _run(*args, transport=transport)
    return ranked


def set_bump(issue: int, bumped: bool, transport: GhTransportInterface | None = None) -> None:
    """Explicitly promote or remove promotion, then leave ordinary triage to the sweep."""
    ensure_labels(transport)
    args = ["issue", "edit", str(issue)]
    if bumped:
        args += ["--add-label", BUMPED]
    else:
        args += ["--remove-label", BUMPED]
    _run(*args, transport=transport)


def summary(items: list[RankedIssue]) -> str:
    lines = ["### Issue triage order", "", "| Rank | Issue | Priority |", "|---:|---|---|"]
    lines += [
        f"| {i} | #{item.number} {item.title} | {'bumped' if item.bumped else item.priority} |"
        for i, item in enumerate(items, 1)
    ]
    return "\n".join(lines) + "\n"
