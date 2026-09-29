# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind a research gap.

Mirrors `vibey/domain/research_gap.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ResearchGapInterface(Protocol):
    """A research topic that was not researched, and why. Carries no source."""

    @property
    def topic(self) -> str: ...

    @property
    def reason(self) -> str: ...

    def statement(self) -> str:
        """The gap as one plain sentence, for the spec a person and REVIEW read."""
        ...
