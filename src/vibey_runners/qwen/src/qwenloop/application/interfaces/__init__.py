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
from qwenloop.application.interfaces.ollama_probe_interface import OllamaProbeInterface
from qwenloop.domain.interfaces import ChatChunkInterface, FollowUpInterface
from qwenloop.domain.model import ChatMessage, ModelProfile, ServerInfo

__all__ = [
    "AutonomousRunnerInterface",
    "BackendSelectorInterface",
    "ClockInterface",
    "DesktopNotifierInterface",
    "InferenceServer",
    "OllamaProbeInterface",
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
    ) -> AsyncIterator[ChatChunkInterface]: ...
    async def stop(self, info: ServerInfo) -> None: ...


class RunStore(Protocol):
    def create(self, run_id: str, metadata: dict[str, object]) -> Path: ...
    def append_event(self, run_id: str, event: dict[str, object]) -> None: ...
    def write_snapshot(self, run_id: str, snapshot: dict[str, object]) -> None: ...
    def read_control(self, run_id: str) -> list[dict[str, object]]: ...
    def take_prompts(self, run_id: str) -> Sequence[FollowUpInterface]:
        """Pending follow-ups, oldest first; each is taken once and never offered again."""
        ...


class ToolExecutor(Protocol):
    async def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]: ...
