# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Paths the merge train never merges unattended: `[merge_train] protected_paths`.

A repository has files whose change should never land on a robot's say-so -- in vibey,
the tests that prove the no-loss gate, the chaos test and the full-cycle system test. A
CODEOWNERS entry plus a ruleset's `require_code_owner_review` asks GitHub to demand the
owner's review for them, but the merge train falls back to `gh pr merge --admin` when a
plain merge is refused, and an admin merge bypasses exactly that review. So the train has
to refuse first, from configuration, before it attempts anything (vibey #213).

It refuses on what it cannot see, too. The changed files come from the paginated REST
listing -- `gh pr view --json files` is a single GraphQL page of at most 100 -- and a
listing shorter than GitHub's own `changedFiles` count, or one that could not be fetched
at all, is a refusal rather than a pass: a guard that reads a truncated list reports the
clean answer about files it never saw.

Patterns are shell-style globs (`fnmatch`) matched case-sensitively against the whole
repository-root path, and `*` crosses `/`, so `tests/live/*` protects that whole tree. A
pattern that could never match such a path -- empty, or starting with `/` as CODEOWNERS
patterns do -- is refused when the configuration loads (`GhConfig`), rather than
protecting nothing in silence.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from fnmatch import fnmatchcase
from typing import Any

__all__ = ["CHANGED_PATHS_KEY", "LISTED_FILES_KEY", "ProtectedPathsGuard"]

# Where the merge train records the listing on the pull request it judges. Not gh's own
# `files` field, which is the truncated GraphQL page this exists to avoid.
CHANGED_PATHS_KEY = "changedPaths"
LISTED_FILES_KEY = "listedFiles"

_KEY = "merge_train.protected_paths"
_HUMAN = "needs a human merge"
# How many protected paths a refusal names before summarising the rest.
_SHOWN = 3


class ProtectedPathsGuard:
    """Implements `ProtectedPathsInterface`."""

    def touched(self, patterns: Sequence[str], paths: Iterable[str]) -> tuple[str, ...]:
        return tuple(
            sorted({path for path in paths if any(fnmatchcase(path, glob) for glob in patterns)})
        )

    def parse_listing(self, text: str) -> tuple[tuple[str, ...], int]:
        # `gh api --paginate` merges the pages of a JSON array on current releases and
        # concatenates them (`[...][...]`) on older ones; decoding value by value reads both.
        decoder = json.JSONDecoder()
        paths: list[str] = []
        files = 0
        index = 0
        while True:
            while index < len(text) and text[index].isspace():
                index += 1
            if index == len(text):
                return tuple(paths), files
            page, index = decoder.raw_decode(text, index)
            if not isinstance(page, list):
                raise TypeError("a pull request's file listing must be a JSON array")
            for entry in page:
                name = entry.get("filename") if isinstance(entry, dict) else None
                if not isinstance(name, str):
                    raise TypeError(f"a listed file has no filename: {entry!r}")
                files += 1
                paths.append(name)
                previous = entry.get("previous_filename")
                if isinstance(previous, str):
                    # Renaming a protected file away is a change to it.
                    paths.append(previous)

    def refusal(self, pr: Mapping[str, Any], patterns: Sequence[str]) -> str | None:
        if not patterns:
            return None
        paths = pr.get(CHANGED_PATHS_KEY)
        if paths is None:
            return f"its changed files could not be listed to check {_KEY} — {_HUMAN}"
        listed = pr.get(LISTED_FILES_KEY)
        total = pr.get("changedFiles")
        if not isinstance(listed, int) or not isinstance(total, int) or listed < total:
            return (
                f"GitHub listed {listed} of {total} changed files, so {_KEY} cannot be"
                f" ruled out — {_HUMAN}"
            )
        hits = self.touched(patterns, paths)
        if not hits:
            return None
        shown = ", ".join(hits[:_SHOWN])
        if len(hits) > _SHOWN:
            shown += f" and {len(hits) - _SHOWN} more"
        return f"touches protected path(s) {shown} ({_KEY}) — {_HUMAN}"
