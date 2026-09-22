# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ports implemented by infrastructure adapters.

Interfaces declare; they never consume. New seams live in their own mirrored
`<module>_interface.py` beside this package's original ports (ADR-0016).
"""

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Protocol

from qwenloop.application.interfaces.backend_selection_interface import (
    BackendSelectorInterface,
)
from qwenloop.application.interfaces.class_contracts import AutonomousRunnerInterface
from qwenloop.application.interfaces.clock_interface import ClockInterface
from qwenloop.application.interfaces.desktop_notifier_interface import DesktopNotifierInterface
from qwenloop.domain.model import ChatChunk, ChatMessage, ModelProfile, ServerInfo

__all__ = [
    "AutonomousRunnerInterface",
    "BackendSelectorInterface",
    "ClockInterface",
    "DesktopNotifierInterface",
    "InferenceServer",
    "RunStore",
    "ToolExecutor",
]


class InferenceServer(Protocol):
    def inspect(self, profile: ModelProfile) -> ServerInfo | None: ...
    async def install(self, profile: ModelProfile) -> Path: ...
    async def start(self, profile: ModelProfile) -> ServerInfo: ...
    async def health(self, info: ServerInfo) -> bool: ...
    def chat_stream(
        self, info: ServerInfo, messages: Sequence[ChatMessage]
    ) -> AsyncIterator[ChatChunk]: ...
    async def stop(self, info: ServerInfo) -> None: ...


class RunStore(Protocol):
    def create(self, run_id: str, metadata: dict[str, object]) -> Path: ...
    def append_event(self, run_id: str, event: dict[str, object]) -> None: ...
    def write_snapshot(self, run_id: str, snapshot: dict[str, object]) -> None: ...
    def read_control(self, run_id: str) -> list[dict[str, object]]: ...


class ToolExecutor(Protocol):
    async def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]: ...
