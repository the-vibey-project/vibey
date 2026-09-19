# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The two shapes an inference server takes: one qwenloop owns, one it only attaches to."""

from typing import Protocol, runtime_checkable

from qwenloop.application.interfaces import InferenceServer
from qwenloop.domain.model import Backend, ModelProfile


@runtime_checkable
class ManagedServerInterface(InferenceServer, Protocol):
    """A server qwenloop spawns on loopback, owns, and stops: llama-server or vllm."""

    binary: str
    backend: Backend


@runtime_checkable
class AttachedServerInterface(InferenceServer, Protocol):
    """A server somebody else runs. qwenloop checks it and talks to it; it never starts
    or stops it, so `start` proves readiness instead of spawning and `stop` does nothing."""

    backend: Backend
    base_url: str
    model: str

    @property
    def profile(self) -> ModelProfile:
        """The unpinned profile a run records for the endpoint's model."""
        ...

    async def check(self) -> str:
        """The served model id matching `model`; RuntimeError says why there is none."""
        ...
