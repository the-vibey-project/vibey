"""The forge's pull requests, read once, and the issues each one says it closes.

Two tools ask the forge the same question from opposite ends. `lane-publish.py` asks "is
this lane's issue already claimed by a pull request?" so it does not open a second one, and
`lane-reap.py` asks "did a pull request that closes this lane's issue merge?" so the ledger
can say the lane landed. One question, one answer: this module is the only place either tool
learns what a pull request closes (10.e). Two copies of the rule would drift, and the drift
would be invisible -- each tool would stay internally consistent while disagreeing with the
other about the same lane.

WHY NOT GITHUB'S SEARCH
-----------------------
`gh pr list --search "Closes #500 in:body"` is full-text search, and full-text search is
built to find documents that are ABOUT something, not documents that SAY something. It
tokenises, it stems and it ranks, so it returns pull requests that mention the words and the
number anywhere, in any order. Measured on 2026-09-23: it answered #268 for issue 400, #269
for 501, #277 for 503 and 444, and #286 for 500 -- and not one of those bodies closes the
issue it was returned for. Five lanes were held as "already published" on that answer and
their check blocks never ran. A dedupe that matches what it should not is a gate that is
silently shut.

So the list is fetched once, bodies included, and the closing references are read with the
same grammar the forge itself uses to close issues: a keyword, then `#N`. That is the thing
that actually closes an issue when the pull request merges, so it is the thing that decides
whether a pull request claims one.

WHAT COUNTS AS CLOSING
----------------------
`close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved`,
any case, an optional colon, then `#N` with N taken whole -- `#12` is never read out of
`#123`. One keyword governs one reference, which is GitHub's rule too: `Closes #1, #2` closes
#1 only, and so claims #1 only. A reference qualified by another repository (`owner/name#N`)
or written as a URL is not read, because a number in someone else's tracker is not this
tracker's issue. "Does not close #332" does close #332 on the forge, and so is read as
closing it here: this reports what the forge will do, not what the prose meant.

A TRUNCATED LIST IS NOT A LIST
------------------------------
`gh pr list` stops at `--limit`. If the forge holds more pull requests than that, the oldest
fall off the end silently, and "no pull request closes this issue" becomes a statement about
a subset nobody chose (10.g). So a page that comes back exactly full is refused as
unreadable rather than trusted, and the limit is declared (`[forge] pr_limit` in storm.toml)
rather than compiled in (12.h).

Module functions rather than a class: every sibling in this directory is a script of plain
functions loaded by path, and this module exists to be the one shared copy of two of them.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

import storm_paths

# Keyword, optional colon, `#N`. `(?!\d)` keeps the number whole, so a closing reference to
# #123 is never read as one to #12. The leading `\b` keeps "encloses" and "disclosed" out.
CLOSING = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*#(\d+)(?!\d)",
    re.IGNORECASE,
)

# A default, not a fact about any machine: storm.toml's `[forge] pr_limit` overrides it.
DEFAULT_LIMIT = 2000


class Unreadable(RuntimeError):
    """The forge could not be read completely, so nothing may be concluded from it."""


class PullRequest(NamedTuple):
    number: int
    state: str  # OPEN, MERGED or CLOSED, as the forge spells them
    head: str
    closes: frozenset[int]


def closes(body: str | None) -> frozenset[int]:
    """Every issue number a pull request body closes, by the forge's own grammar."""
    return frozenset(int(n) for n in CLOSING.findall(body or ""))


def limit(root: Path) -> int:
    """How many pull requests one read may return, declared or defaulted."""
    declared = storm_paths.declared(root, "forge", "pr_limit")
    return int(declared) if declared is not None else DEFAULT_LIMIT


def pull_requests(cwd: Path, repo: str | None, most: int) -> list[PullRequest]:
    """Every pull request on the forge, newest first, or `Unreadable` saying why not.

    One call for every lane. Raising rather than returning an empty list, because an empty
    list and an unreachable forge are the same value and opposite facts -- the first says
    nothing was ever published, the second says nobody could find out.
    """
    argv = ["gh", "pr", "list", "--state", "all", "--limit", str(most)]
    argv += ["--json", "number,state,headRefName,body"]
    if repo:
        argv += ["--repo", repo]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=300, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unreadable(f"gh could not be run: {exc}") from exc
    if done.returncode != 0:
        raise Unreadable(f"gh pr list failed: {done.stderr.strip()[:160]}")
    try:
        rows = json.loads(done.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise Unreadable(f"gh pr list returned something that is not JSON: {exc}") from exc
    if len(rows) >= most:
        raise Unreadable(
            f"the forge returned {len(rows)} pull requests, the whole of the limit, so the "
            f"oldest may be missing -- raise [forge] pr_limit in storm.toml"
        )
    return [
        PullRequest(
            number=int(row["number"]),
            state=str(row.get("state", "")),
            head=str(row.get("headRefName", "")),
            closes=closes(row.get("body")),
        )
        for row in rows
    ]


def closing(prs: list[PullRequest], issue: int | None) -> list[PullRequest]:
    """The pull requests that close `issue`, in the order given (newest first)."""
    if issue is None:
        return []
    return [pr for pr in prs if issue in pr.closes]
