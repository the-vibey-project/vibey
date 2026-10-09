# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The backlog grounding: what an issue's text is allowed to make the lane quote."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import backlog_grounding as bg


class FakeRepo:
    """A tracked tree held in memory."""

    def __init__(self, files: dict[str, str], hits: dict[str, list[str]] | None = None) -> None:
        self._files = files
        self._hits = hits or {}

    def tracked(self) -> Sequence[str]:
        return list(self._files)

    def text(self, path: str) -> str:
        return self._files.get(path, "")

    def excerpt(self, path: str, lines: int) -> tuple[int, str]:
        body = self.text(path).splitlines()
        return len(body), "\n".join(line[:160] for line in body[:lines])

    def grep(self, term: str, limit: int) -> Sequence[str]:
        return self._hits.get(term, [])[:limit]


CLAUDE = """\
# CLAUDE.md

## Non-negotiables

- **Never block a worker on a human.** Human input is a parked job.
- **`domain/` stays pure.** No I/O.

## Layer map

- **Not a non-negotiable.** Another section.
"""


def grounding(files: dict[str, str], **kwargs: object) -> bg.IssueGrounding:
    return bg.IssueGrounding(
        FakeRepo({"CLAUDE.md": CLAUDE, **files}, kwargs.pop("hits", None)), **kwargs
    )  # type: ignore[arg-type]


def test_it_quotes_the_tracked_files_the_issue_names_and_nothing_else() -> None:
    files = {"src/a.py": "one\ntwo\nthree\n", "docs/b.md": "b\n"}
    issue = "Fix src/a.py (see ./docs/b.md, and /etc/passwd, and src/missing.py)."
    out = grounding(files).ground(issue)
    assert "### src/a.py (3 lines)" in out and "### docs/b.md (1 lines)" in out
    assert "passwd" not in out and "missing.py" not in out


def test_a_long_file_is_cut_loudly_and_the_named_files_are_capped() -> None:
    files = {f"f{n}.py": "\n".join(str(i) for i in range(100)) for n in range(6)}
    issue = " ".join(f"f{n}.py" for n in range(6))
    out = grounding(files, max_files=2, excerpt_lines=5).ground(issue)
    assert "### f0.py (100 lines; first 5 shown)" in out
    assert "[4 more named file(s) not shown: f2.py, f3.py, f4.py, f5.py]" in out
    assert "f2.py (" not in out.replace("f2.py, f3.py", "")


def test_it_says_when_the_issue_names_no_tracked_file() -> None:
    assert "names no tracked file" in grounding({}).ground("Something is slow.")


def test_identifiers_are_searched_and_a_miss_is_said_out_loud() -> None:
    hits = {"PatchGuard": ["scripts/x.py:1:class PatchGuard", "scripts/y.py:2:PatchGuard()"]}
    out = grounding({}, hits=hits, hits_per_term=1).ground(
        "Use `PatchGuard`, not `NoSuchThing`; run `git status` and `a b c`."
    )
    assert "PatchGuard: \n  scripts/x.py:1:class PatchGuard" in out
    assert "scripts/y.py" not in out  # capped at one hit
    assert "NoSuchThing: no hit in tracked files" in out
    assert "git status" not in out and "a b c" not in out  # a command is not an identifier


def test_identifiers_are_capped_and_the_cap_is_said() -> None:
    issue = " ".join(f"`name{n}`" for n in range(9))
    out = grounding({}, max_terms=3).ground(issue)
    assert "[6 more identifier(s) not searched]" in out


def test_the_non_negotiables_are_the_headlines_of_that_section_only() -> None:
    out = grounding({}).ground("x")
    assert "- Never block a worker on a human." in out
    assert "- `domain/` stays pure." in out
    assert "Not a non-negotiable" not in out


def test_the_git_repository_only_reads_tracked_files(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=tmp_path, check=True
        )

    git("init", "-q")
    (tmp_path / "tracked.py").write_text("def needle():\n    return 1\n")
    (tmp_path / "untracked.py").write_text("needle\n")
    git("add", "tracked.py")
    git("commit", "-qm", "i")
    repo = bg.GitRepository(tmp_path)
    assert list(repo.tracked()) == ["tracked.py"]
    assert repo.excerpt("tracked.py", 1) == (2, "def needle():")
    assert repo.grep("needle", 5) == ["tracked.py:1:def needle():"]
    assert repo.text("nope.py") == "" and repo.grep("zzz", 5) == []


def test_the_cli_prints_the_grounding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert bg.GroundingCli(tmp_path).run("nothing named") == 0
    assert "Grounding, read for you" in capsys.readouterr().out
