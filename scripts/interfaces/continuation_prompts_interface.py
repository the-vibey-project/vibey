# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/continuation_prompts.py` implements. Interfaces declare; they never consume.

A *fact source* reads what the repository says about itself today. A *reference probe* says
whether one thing a prompt names still exists. A *command runner* runs one declared command
and returns its output. A *renderer* turns facts into the generated blocks of the pages.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class FactSourceInterface(Protocol):
    """What the repository declares about itself: version, decisions, lanes, skills."""

    def facts(self) -> Mapping[str, Any]:
        """Every fact the generated blocks show, read from tracked files only."""
        ...


class ReferenceProbeInterface(Protocol):
    """Whether one thing a prompt names still exists."""

    def missing(self, text: str) -> Sequence[str]:
        """Each reference in `text` that does not resolve, described in one line."""
        ...


class CommandRunnerInterface(Protocol):
    """Runs one declared command; never raises on a failing command."""

    def run(self, command: str, timeout_s: float) -> tuple[int, str]:
        """The exit code and the combined output (a timeout is code 124)."""
        ...


class PageRendererInterface(Protocol):
    """Turns the facts into the text of every generated block."""

    def blocks(self, prompt_id: str | None) -> Mapping[str, str]:
        """The blocks for one prompt's page, or for the index when `prompt_id` is None."""
        ...


class PatchPathsInterface(Protocol):
    """Reads what a patch changes the way the tool that applies it does."""

    def touched(self, patch: Path) -> list[tuple[str, str]] | None:
        """(status, path) for every path the patch changes -- both sides of a rename -- or
        None when the patch cannot be applied at all."""
        ...


class PatchStatsInterface(Protocol):
    """Counts the lines a patch adds and removes, per path, the way git applies it."""

    def stats(self, patch: Path) -> list[tuple[str, int, int]] | None:
        """(path, added, removed) for every path, or None when the patch cannot be read."""
        ...


class PatchShrinkRuleInterface(Protocol):
    """Says whether a patch guts a file."""

    def shrunk(self, patch: Path) -> Sequence[str]:
        """Every path the patch removes more than the declared limit of lines from, a deleted
        or emptied file included. An unreadable patch is refused."""
        ...


class PatchGuardInterface(Protocol):
    """Says which paths a patch from an automated run may not touch."""

    def refused(self, patch: Path) -> Sequence[str]:
        """Every path the patch changes that a protected pattern matches, and every file it
        adds outside the declared `allowed_new` roots. A patch that cannot be read is refused."""
        ...


class PatchTestRuleInterface(Protocol):
    """Says whether a patch for a prompt that promises a tested change carries a test."""

    def missing(self, patch: Path, prompt: str) -> Sequence[str]:
        """What is wrong with `patch` for `prompt`: empty when the prompt needs no test or the
        patch adds or changes one, else one line saying no test was touched."""
        ...


class RunReceiptInterface(Protocol):
    """Says what a run left behind, and whether that is enough to believe its patch."""

    def transcript(self, cwd: Path) -> str:
        """The run's recorded words and tool calls, read from the run store under `cwd`."""
        ...

    def problems(self, out: Path) -> list[str]:
        """Why the hand-over directory is not enough evidence; empty when it is."""
        ...


class ReplyDefuserInterface(Protocol):
    """Makes model output safe to post as a comment."""

    def defuse(self, text: str) -> str:
        """The text with mentions and chat triggers neutralised, cut loudly to the cap."""
        ...

    def fenced(self, text: str, info: str = "text") -> str:
        """`text` inside a code fence that nothing in it can close."""
        ...
