# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for concrete Claude infrastructure adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from claudeloop.application.dto import BackendStatus, ToolCallStatus
from claudeloop.application.interfaces.agent import AgentGateway, CapacityProbe
from claudeloop.application.interfaces.class_contracts import TurnOutcomeInterface
from claudeloop.application.interfaces.doctor import DoctorEnvironment


@runtime_checkable
class ClaudeAgentGatewayInterface(AgentGateway, Protocol):
    def set_event_listener(self, on_event: object | None) -> None: ...

    def resolve_tool_approval(self, request_id: str, *, allow: bool, reason: str = "") -> bool: ...


@runtime_checkable
class ClaudeCapacityProbeInterface(CapacityProbe, Protocol):
    def set_model(self, model: str | None) -> None: ...


@runtime_checkable
class TurnAccumulatorInterface(Protocol):
    @property
    def thinking_text(self) -> str: ...

    @property
    def tool_events(self) -> tuple[dict[str, object], ...]: ...

    def feed(self, message: object) -> None: ...

    def build(self) -> TurnOutcomeInterface: ...


@runtime_checkable
class RunnerConfigInterface(Protocol):
    @property
    def max_turns(self) -> int | None: ...

    @property
    def max_dollars(self) -> float | None: ...

    @property
    def model(self) -> str | None: ...

    @property
    def effort(self) -> str | None: ...

    @property
    def profile(self) -> str | None: ...

    @property
    def backend(self) -> object: ...

    def aliases(self) -> object: ...

    def resolved_profile(self) -> object: ...

    def effective_log_chatter(self) -> str: ...

    def effective_partial_messages(self) -> bool: ...


@runtime_checkable
class RealDoctorEnvironmentInterface(DoctorEnvironment, Protocol):
    def find_bundled_claude_cli(self) -> str | None: ...

    def probe_backend(self, base_url: str, auth_token: str) -> BackendStatus: ...

    def probe_tool_calling(self, base_url: str, auth_token: str, model: str) -> ToolCallStatus: ...


@runtime_checkable
class RunMetaInterface(Protocol):
    @property
    def run_id(self) -> str: ...

    @property
    def pid(self) -> int: ...

    @property
    def cwd(self) -> str: ...

    @property
    def started_at(self) -> str: ...

    @property
    def session_id(self) -> str | None: ...

    @property
    def status(self) -> str: ...

    @property
    def attempt(self) -> int: ...

    @property
    def backend(self) -> str | None: ...

    @property
    def profile(self) -> str | None: ...

    def to_dict(self) -> Mapping[str, object]: ...

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RunMetaInterface: ...
