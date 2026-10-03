# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/continuation_prompts.py` implements. Interfaces declare; they never consume.

A *fact source* reads what the repository says about itself today. A *reference probe* says
whether one thing a prompt names still exists. A *command runner* runs one declared command
and returns its output. A *renderer* turns facts into the generated blocks of the pages.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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


class PatchGuardInterface(Protocol):
    """Says which paths a patch from an automated run may not touch."""

    def refused(self, patch: str) -> Sequence[str]:
        """Every path the patch changes that a declared protected pattern matches."""
        ...


class ReplyDefuserInterface(Protocol):
    """Makes model output safe to post as a comment."""

    def defuse(self, text: str) -> str:
        """The text with mentions and chat triggers neutralised, cut loudly to the cap."""
        ...
