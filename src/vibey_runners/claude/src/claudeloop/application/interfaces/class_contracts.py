# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for the Claude runner's application values and coordinator."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from claudeloop.application.dto import RunResult


@runtime_checkable
class TurnOutcomeInterface(Protocol):
    @property
    def signals(self) -> object: ...

    @property
    def verdict(self) -> object | None: ...

    @property
    def output_text(self) -> str: ...

    @property
    def session_id(self) -> str | None: ...

    @property
    def cost_usd(self) -> float: ...

    @property
    def raw_events(self) -> tuple[dict[str, object], ...]: ...

    @property
    def input_tokens(self) -> int: ...

    @property
    def output_tokens(self) -> int: ...


@runtime_checkable
class BackendStatusInterface(Protocol):
    @property
    def reachable(self) -> bool: ...

    @property
    def detail(self) -> str: ...

    @property
    def models(self) -> tuple[str, ...] | None: ...


@runtime_checkable
class ToolCallStatusInterface(Protocol):
    @property
    def supported(self) -> bool | None: ...

    @property
    def detail(self) -> str: ...


@runtime_checkable
class AutonomousRunnerInterface(Protocol):
    async def run(self, *, initial_prompt: str, continue_prompt: str) -> RunResult: ...
