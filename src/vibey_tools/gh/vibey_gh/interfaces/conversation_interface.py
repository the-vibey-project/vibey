# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for reading one conversation thread (ADR-0016).

A mention is answered against a thread fetched from GitHub, and two facts about that thread
decide how far the answer may reach: whether it is a pull request, and which comment the
mention actually is. Both are answered in exactly one place, behind this contract, so the
evaluation, the briefing and the command line cannot disagree about either.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConversationThreadInterface(Protocol):
    """One fetched issue or pull request, and the comments a mention can name on it."""

    @property
    def number(self) -> int:
        """The issue or pull request number."""
        ...

    @property
    def is_pull_request(self) -> bool:
        """Whether the thread is a pull request, read from what GitHub returned for it."""
        ...

    def comment(self, wanted: str) -> dict[str, Any]:
        """The comment `wanted` names, or the newest one on the thread when it is empty.

        An ID that names no comment on this thread is an error, never a default: raises
        `RuntimeError` rather than answering some other comment in its place.
        """
        ...
