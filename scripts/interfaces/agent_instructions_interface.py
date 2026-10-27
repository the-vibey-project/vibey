# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the generated agent front doors (ADR-0016)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentInstructionsInterface(Protocol):
    """Renders CLAUDE.md, AGENTS.md and GEMINI.md from one declared source (#1688)."""

    def agents(self) -> list[str]:
        """The doors the source declares, by name."""
        ...

    def problems(self) -> list[str]:
        """What is wrong with the source itself: an id twice, an unknown agent, an empty block."""
        ...

    def render(self, agent: str) -> str:
        """The whole file for `agent`, the provisioner's marker block carried over from disk."""
        ...

    def differing(self) -> list[str]:
        """One sentence per file on disk that is not what `render` makes of the source."""
        ...
