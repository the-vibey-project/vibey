# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey serve`.

Mirrors `vibey/cli/serve.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ServeCommandInterface(Protocol):
    """Runs the hub, and prints its OpenAPI document."""

    def openapi(self) -> str:
        """The OpenAPI 3.1 document, sorted and newline-terminated; no database."""
        ...

    async def run(self, *, host: str | None, port: int | None) -> None:
        """Serves until stopped. Exits 2 for an undeclared non-loopback address."""
        ...

    def exposure_line(self) -> bool:
        """Prints `vibey doctor`'s `hub-exposure` line; False only on FAIL."""
        ...
