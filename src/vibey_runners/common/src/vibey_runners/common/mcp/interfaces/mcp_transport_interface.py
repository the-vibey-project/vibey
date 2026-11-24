# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How an MCP session reaches its server: a line stream in, a line writer out (SP-LOOPS
Phase 5, Task 3)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class McpTransportInterface(Protocol):
    async def open(self) -> tuple[asyncio.StreamReader, Callable[[str], Awaitable[None]]]:
        """Reach the server. Returns the stream its lines arrive on and a writer that sends
        one complete line. Raises when the server cannot be reached at all."""
        ...

    async def close(self, grace_seconds: float) -> None:
        """Let the server go: tell it to finish, give it `grace_seconds`, then end it.
        Idempotent, and never raises."""
        ...

    def describe(self) -> str:
        """The server's name and kind, for a message: for HTTP the host only. Never an argv
        tail, a query string or an environment value."""
        ...
