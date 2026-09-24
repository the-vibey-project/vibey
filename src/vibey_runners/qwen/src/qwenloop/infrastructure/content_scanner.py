# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Line-by-line content search over files already confined to a worktree.

Stdlib only, on purpose: a regex search runs this module in a child interpreter that is
killed at `search_timeout_seconds`, because a model-supplied pattern can backtrack for
longer than any turn should wait. A literal search runs it in-process.
"""

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path


class ContentScanner:
    """Finds matching lines, and says which candidate files it could not search.

    A skipped file (too large, binary, not UTF-8, unreadable) is counted and named in the
    answer, and makes the answer incomplete, so an empty `matches` is never mistaken for
    proof that the text is absent.
    """

    def __init__(self, *, max_file_bytes: int, max_line_chars: int, max_skipped_examples: int):
        self._max_file_bytes = max_file_bytes
        self._max_line_chars = max_line_chars
        self._max_skipped_examples = max_skipped_examples

    def scan(
        self, candidates: Sequence[tuple[str, str]], pattern: str, flags: int, limit: int
    ) -> dict[str, object]:
        """Match `pattern` against every line of each (relative, absolute) candidate path,
        stopping once more than `limit` lines match."""
        matcher = re.compile(pattern, flags)
        matches: list[str] = []
        skipped: list[tuple[str, str]] = []
        truncated = False
        for relative, path in candidates:
            text, reason = self._text(Path(path))
            if text is None:
                skipped.append((relative, reason))
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if not matcher.search(line):
                    continue
                if len(matches) == limit:
                    truncated = True
                    break
                matches.append(f"{relative}:{number}: {self._clip(line)}")
            if truncated:
                break
        return self._answer(matches, truncated, skipped)

    def _answer(
        self, matches: list[str], truncated: bool, skipped: list[tuple[str, str]]
    ) -> dict[str, object]:
        answer: dict[str, object] = {
            "matches": matches,
            "count": len(matches),
            "truncated": truncated,
            "complete": not truncated and not skipped,
        }
        if skipped:
            reasons = ", ".join(sorted({reason for _, reason in skipped}))
            answer["skipped"] = {
                "count": len(skipped),
                "examples": [
                    f"{relative} ({reason})"
                    for relative, reason in skipped[: self._max_skipped_examples]
                ],
            }
            answer["note"] = (
                f"{len(skipped)} file(s) were not searched ({reasons}), so a missing match "
                "is not evidence that the text is absent there"
            )
        return answer

    def _text(self, file: Path) -> tuple[str | None, str]:
        """A file's text, or None and the reason it cannot be searched."""
        try:
            if file.stat().st_size > self._max_file_bytes:
                return None, "larger than max_file_bytes"
            data = file.read_bytes()
        except OSError:
            return None, "unreadable"
        if b"\0" in data:
            return None, "binary"
        try:
            return data.decode("utf-8"), ""
        except UnicodeDecodeError:
            return None, "not UTF-8"

    def _clip(self, line: str) -> str:
        limit = self._max_line_chars
        return line if len(line) <= limit else f"{line[:limit]}…"

    @classmethod
    def run_stdio(cls) -> None:
        """The child-process entry: one JSON request on stdin, one JSON answer on stdout."""
        request = json.load(sys.stdin)
        scanner = cls(
            max_file_bytes=int(request["max_file_bytes"]),
            max_line_chars=int(request["max_line_chars"]),
            max_skipped_examples=int(request["max_skipped_examples"]),
        )
        candidates = [(str(relative), str(path)) for relative, path in request["candidates"]]
        answer = scanner.scan(
            candidates, str(request["pattern"]), int(request["flags"]), int(request["limit"])
        )
        json.dump(answer, sys.stdout)
