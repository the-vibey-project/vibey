# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for qwenloop's OpenAI-compatible server adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from qwenloop.application.interfaces import InferenceServer


@runtime_checkable
class OpenAIServerInterface(InferenceServer, Protocol):
    @property
    def binary(self) -> str: ...

    @property
    def backend(self) -> object: ...


@runtime_checkable
class VllmServerInterface(OpenAIServerInterface, Protocol):
    """The vLLM managed-server specialization."""


@runtime_checkable
class OpenAICompatServerInterface(InferenceServer, Protocol):
    @property
    def profile(self) -> object: ...

    async def check(self) -> None: ...
