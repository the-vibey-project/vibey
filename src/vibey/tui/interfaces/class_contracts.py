# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interfaces for dashboard state and replay controls."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class DashboardStateInterface(Protocol):
    @property
    def project_id(self) -> UUID: ...

    @property
    def project_name(self) -> str: ...

    @property
    def repo_path(self) -> Path: ...

    @property
    def phase(self) -> object: ...

    @property
    def cycle(self) -> int: ...

    @property
    def max_cycles(self) -> int: ...

    @property
    def visual_decision(self) -> str | None: ...

    @property
    def deployment_decision(self) -> str | None: ...

    @property
    def queue_depth(self) -> Mapping[object, int]: ...

    @property
    def circuits(self) -> Sequence[object]: ...

    @property
    def active_worktrees(self) -> tuple[str, ...]: ...

    @property
    def ledger_tail(self) -> tuple[object, ...]: ...

    @property
    def phase_label(self) -> str: ...


@runtime_checkable
class StatusPanelInterface(Protocol):
    @property
    def state(self) -> DashboardStateInterface | None: ...

    def watch_state(self, state: DashboardStateInterface | None) -> None: ...


@runtime_checkable
class VibeyReplayAppInterface(Protocol):
    @property
    def current_step(self) -> int: ...

    @property
    def is_playing(self) -> bool: ...

    def compose(self) -> object: ...

    def watch_current_step(self, step: int) -> None: ...

    def action_next_step(self) -> None: ...

    def action_prev_step(self) -> None: ...

    def action_toggle_play(self) -> None: ...
