# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey acp unload` (ADR-0101). Declares only."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AcpUnloadCommandInterface(Protocol):
    def run(self) -> int:
        """Stop and unload every unit `vibey acp` loaded, in the user's own domain, and delete
        each unit file that is still exactly what vibey wrote (never one the operator edited).
        Idempotent; prints what it did. 0 when everything was done, 1 when something failed."""
        ...
