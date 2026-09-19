# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for qwenloop's application coordinator."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from qwenloop.domain.model import ModelProfile, RunState, ServerInfo


@runtime_checkable
class AutonomousRunnerInterface(Protocol):
    async def run(
        self,
        *,
        run_id: str,
        plan: str,
        cwd: Path,
        profile: ModelProfile,
        server_info: ServerInfo,
        max_turns: int,
    ) -> RunState: ...
