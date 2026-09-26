# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for qwenloop's backend and endpoint value objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BackendInterface(Protocol):
    @property
    def value(self) -> str: ...


@runtime_checkable
class ToolLimitsInterface(Protocol):
    """What one tool call may read or return."""

    @property
    def max_read_chars(self) -> int: ...

    @property
    def max_search_matches(self) -> int: ...

    @property
    def max_find_results(self) -> int: ...

    @property
    def max_line_chars(self) -> int: ...

    @property
    def max_file_bytes(self) -> int: ...

    @property
    def max_skipped_examples(self) -> int: ...

    @property
    def search_timeout_seconds(self) -> float: ...

    @property
    def skip_dirs(self) -> tuple[str, ...]: ...


@runtime_checkable
class RunnerIdentityInterface(Protocol):
    """Which engine a runner process is: its name, its settings' prefix, its model."""

    @property
    def name(self) -> str: ...

    @property
    def env_prefix(self) -> str: ...

    @property
    def default_model(self) -> str: ...

    @property
    def env_config(self) -> str: ...

    @property
    def env_base_url(self) -> str: ...

    @property
    def env_model(self) -> str: ...

    @property
    def env_api_key(self) -> str: ...


@runtime_checkable
class QwenConfigInterface(Protocol):
    @property
    def backend(self) -> BackendInterface: ...

    @property
    def portable_profile(self) -> str: ...

    @property
    def nvidia_profile(self) -> str: ...

    @property
    def idle_timeout_seconds(self) -> int: ...

    @property
    def startup_timeout_seconds(self) -> int: ...

    @property
    def context_window(self) -> int: ...

    @property
    def max_turns(self) -> int: ...

    @property
    def max_empty_reply_retries(self) -> int: ...

    @property
    def max_recorded_argument_chars(self) -> int: ...

    @property
    def empty_reply_reasoning_excerpt_chars(self) -> int: ...

    @property
    def base_url(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def endpoint_timeout_seconds(self) -> int: ...

    @property
    def tools(self) -> ToolLimitsInterface: ...

    @property
    def endpoint_configured(self) -> bool: ...

    @property
    def endpoint_url(self) -> str: ...


@runtime_checkable
class ChatChunkInterface(Protocol):
    """One piece of a model reply, as every inference adapter hands it to the runner."""

    @property
    def text(self) -> str: ...

    @property
    def tool_call(self) -> dict[str, Any] | None: ...

    @property
    def input_tokens(self) -> int: ...

    @property
    def output_tokens(self) -> int: ...

    @property
    def timings(self) -> Mapping[str, float] | None: ...

    @property
    def finish_reason(self) -> str | None: ...

    @property
    def reasoning(self) -> str | None: ...


@runtime_checkable
class FollowUpInterface(Protocol):
    """A person's message for a running run, taken from its control inbox once."""

    @property
    def id(self) -> str: ...

    @property
    def text(self) -> str: ...


@runtime_checkable
class ToolCallParseErrorInterface(Protocol):
    @property
    def detail(self) -> str: ...


@runtime_checkable
class ServerInfoInterface(Protocol):
    @property
    def backend(self) -> BackendInterface: ...

    @property
    def profile(self) -> str: ...

    @property
    def endpoint(self) -> str: ...

    @property
    def owned(self) -> bool: ...

    @property
    def healthy(self) -> bool: ...

    @property
    def pid(self) -> int | None: ...

    @property
    def token(self) -> str: ...

    @property
    def model(self) -> str: ...


@runtime_checkable
class HardwareInterface(Protocol):
    @property
    def system(self) -> str: ...

    @property
    def nvidia_vram_bytes(self) -> int: ...


@runtime_checkable
class BackendChoiceInterface(Protocol):
    @property
    def backend(self) -> BackendInterface: ...

    @property
    def reason(self) -> str: ...
