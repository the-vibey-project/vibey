# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for qwenloop's backend and endpoint value objects."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BackendInterface(Protocol):
    @property
    def value(self) -> str: ...


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
    def base_url(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def endpoint_timeout_seconds(self) -> int: ...

    @property
    def endpoint_configured(self) -> bool: ...

    @property
    def endpoint_url(self) -> str: ...


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
