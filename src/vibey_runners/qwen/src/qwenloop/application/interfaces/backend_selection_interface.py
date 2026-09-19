# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for choosing which inference backend a run uses."""

from typing import Protocol, runtime_checkable

from qwenloop.domain.model import Backend, BackendChoice, Hardware


@runtime_checkable
class BackendSelectorInterface(Protocol):
    """Deterministic: the same request, hardware, and configuration give the same backend."""

    def select(
        self,
        requested: Backend,
        hardware: Hardware,
        *,
        vllm_installed: bool,
        endpoint_configured: bool,
    ) -> BackendChoice:
        """An explicit request wins, then a configured endpoint, then the hardware."""
        ...
