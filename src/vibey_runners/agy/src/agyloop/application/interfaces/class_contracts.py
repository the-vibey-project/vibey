# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contract for the Antigravity autonomous runner."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agyloop.application.dto import RunResult


@runtime_checkable
class AutonomousRunnerInterface(Protocol):
    async def run(self, *, initial_prompt: str, continue_prompt: str) -> RunResult: ...
