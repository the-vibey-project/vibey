# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/adamsteinberger)).
"""Contracts for the local Ollama service."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OllamaStatusInterface(Protocol):
    @property
    def installed(self) -> bool: ...

    @property
    def running(self) -> bool: ...

    @property
    def model_present(self) -> bool: ...

    @property
    def detail(self) -> str: ...

    @property
    def ready(self) -> bool: ...


@runtime_checkable
class OllamaInstallResultInterface(Protocol):
    @property
    def ok(self) -> bool: ...

    @property
    def changed(self) -> bool: ...

    @property
    def detail(self) -> str: ...

    @property
    def status(self) -> OllamaStatusInterface: ...


@runtime_checkable
class OllamaLocalServiceInterface(Protocol):
    def status(self, model: str | None = None) -> OllamaStatusInterface: ...

    def install(
        self, *, model: str, confirm: bool = True, pull: bool = True
    ) -> OllamaInstallResultInterface: ...


__all__ = [
    "OllamaInstallResultInterface",
    "OllamaLocalServiceInterface",
    "OllamaStatusInterface",
]
