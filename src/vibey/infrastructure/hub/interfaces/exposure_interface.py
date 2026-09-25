# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind judging a running hub's exposure.

Mirrors `vibey/infrastructure/hub/exposure.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.hub.exposure import ExposureFinding
    from vibey.infrastructure.hub.interfaces.local_token_interface import (
        LocalTokenStoreInterface,
    )
    from vibey.infrastructure.hub.settings import HubSettings


@runtime_checkable
class HubExposureCheckInterface(Protocol):
    """PASS for loopback or declared LAN, FAIL for undeclared, UNKNOWN for no evidence."""

    def run(self, settings: HubSettings, store: LocalTokenStoreInterface) -> ExposureFinding:
        """The `hub-exposure` doctor line."""
        ...
