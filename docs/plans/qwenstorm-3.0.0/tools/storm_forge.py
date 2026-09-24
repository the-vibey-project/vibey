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

A WRONG SHAPE IS NOT A LIST EITHER
----------------------------------
`gh` can succeed and still hand back JSON that is not a list of pull requests -- an error
envelope object, say. Iterating an object walks its keys, and the first `row["number"]` on a
string raised TypeError, so publish and reap crashed instead of failing closed. The decoded
value is checked: a list, of objects, each carrying the four fields read, each of the right
type. Anything else is `Unreadable`, the same as a failed call.

A class behind `interfaces/storm_forge_interface.py` (ADR-0016): the tools take the
interface, and a test hands them a double instead of patching `subprocess`.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import storm_paths

# The declaration, loaded by its FILE PATH -- the way `lane_environment.py`'s and
# `storm_trust.py`'s are -- and never imported as `interfaces.storm_forge_interface`. That
# name resolves through `sys.path`, where `tools/interfaces/` is only a namespace package:
# any regular top-level `interfaces` package anywhere on the path outranks it, and the tools
# would then read some other project's `PullRequest` without a word. A path cannot be
# shadowed. Loaded here, once, so the two value types the contract speaks in are one class
# each for every caller, and an `except Unreadable` catches what this raises.
_DECLARED = importlib.util.spec_from_file_location(
    "storm_forge_interface",
    Path(__file__).absolute().parent / "interfaces" / "storm_forge_interface.py",
)
_INTERFACE = importlib.util.module_from_spec(_DECLARED)  # type: ignore[arg-type]
_DECLARED.loader.exec_module(_INTERFACE)  # type: ignore[union-attr]
PullRequest = _INTERFACE.PullRequest
StormForgeInterface = _INTERFACE.StormForgeInterface
Unreadable = _INTERFACE.Unreadable

__all__ = ["PullRequest", "StormForge", "StormForgeInterface", "Unreadable"]


class StormForge:
    """The forge's pull requests, read in one call, and the closing references in each."""

    # Keyword, optional colon, `#N`. `(?!\d)` keeps the number whole, so a closing reference
    # to #123 is never read as one to #12. The leading `\b` keeps "encloses" and "disclosed"
    # out.
    CLOSING = re.compile(
        r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*#(\d+)(?!\d)",
        re.IGNORECASE,
    )
    # A default, not a fact about any machine: storm.toml's `[forge] pr_limit` overrides it.
    DEFAULT_LIMIT = 2000
    # Each field read from a row, and the types the forge sends it as. `body` is null for a
    # pull request opened with no description.
    FIELDS: dict[str, tuple[type, ...]] = {
        "number": (int,),
        "state": (str,),
        "headRefName": (str,),
        "body": (str, type(None)),
    }

    def __init__(
        self,
        cwd: Path,
        repo: str | None,
        most: int,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.cwd, self.repo, self.most, self.runner = cwd, repo, most, runner

    @classmethod
    def declared(cls, root: Path, cwd: Path, repo: str | None) -> StormForge:
        """A forge whose read limit is the one `storm.toml` declares, or the default."""
        declared = storm_paths.declared(root, "forge", "pr_limit")
        return cls(cwd, repo, int(declared) if declared is not None else cls.DEFAULT_LIMIT)

    def closes(self, body: str | None) -> frozenset[int]:
        """Every issue number a pull request body closes, by the forge's own grammar."""
        return frozenset(int(n) for n in self.CLOSING.findall(body or ""))

    def pull_requests(self) -> list[PullRequest]:
        """Every pull request on the forge, newest first, or `Unreadable` saying why not.

        One call for every lane. Raising rather than returning an empty list, because an
        empty list and an unreachable forge are the same value and opposite facts -- the
        first says nothing was ever published, the second says nobody could find out.
        """
        argv = ["gh", "pr", "list", "--state", "all", "--limit", str(self.most)]
        argv += ["--json", ",".join(("number", "state", "headRefName", "body"))]
        if self.repo:
            argv += ["--repo", self.repo]
        try:
            done = self.runner(argv, capture_output=True, text=True, timeout=300, cwd=self.cwd)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Unreadable(f"gh could not be run: {exc}") from exc
        if done.returncode != 0:
            raise Unreadable(f"gh pr list failed: {done.stderr.strip()[:160]}")
        try:
            rows = json.loads(done.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise Unreadable(f"gh pr list returned something that is not JSON: {exc}") from exc
        if not isinstance(rows, list):
            raise Unreadable(f"gh pr list returned a {type(rows).__name__}, not a list")
        if len(rows) >= self.most:
            raise Unreadable(
                f"the forge returned {len(rows)} pull requests, the whole of the limit, so "
                f"the oldest may be missing -- raise [forge] pr_limit in storm.toml"
            )
        return [self._row(row) for row in rows]

    def closing(self, prs: list[PullRequest], issue: int | None) -> list[PullRequest]:
        """The pull requests in `prs` that close `issue`, in the order given (newest first)."""
        if issue is None:
            return []
        return [pr for pr in prs if issue in pr.closes]

    def heads(self, prs: list[PullRequest]) -> dict[str, tuple[int, str]]:
        """Each head ref's newest pull request, as (number, state).

        Keyed by the WHOLE head ref, not by lane slug: lane-reap's worktree pass looks up
        `docs/...` and `fix/...` branches too, and a map keyed on slugs held only `lane/*`.
        The list is newest first, so the first one seen is the live one -- a branch
        republished after a closed attempt is judged on the new request.
        """
        out: dict[str, tuple[int, str]] = {}
        for pr in prs:
            if pr.head and pr.head not in out:
                out[pr.head] = (pr.number, pr.state)
        return out

    def _row(self, row: Any) -> PullRequest:
        """One decoded row as a `PullRequest`, or `Unreadable` if it is not one."""
        if not isinstance(row, dict):
            raise Unreadable(f"gh pr list returned a row that is a {type(row).__name__}")
        for field, kinds in self.FIELDS.items():
            if field not in row:
                raise Unreadable(f"gh pr list returned a row without {field!r}")
            # `bool` is an `int` to isinstance, and `true` is not a pull request number.
            if not isinstance(row[field], kinds) or isinstance(row[field], bool):
                raise Unreadable(f"gh pr list returned a {field!r} that is not {kinds}")
        return PullRequest(
            number=row["number"],
            state=row["state"],
            head=row["headRefName"],
            closes=self.closes(row["body"]),
        )
