# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/acp/stdio_transport.py` (ADR-0016). Declares only."""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable


@runtime_checkable
class StdioTransportInterface(Protocol):
    """stdin and a protocol-only stdout for `vibey acp`."""

    def guard(self) -> int:
        """Keep a private, non-inheritable duplicate of stdout for protocol frames; point fd 1
        at stderr and `sys.stdout` at `sys.stderr`. Returns the private fd."""
        ...

    async def reader(self, limit: int) -> asyncio.StreamReader:
        """A reader on stdin, with `limit` as its line limit; it reaches EOF when stdin does."""
        ...

    async def write_line(self, line: str) -> None:
        """Write one whole frame (trailing newline included) to the private stdout, or to
        stdout itself before `guard`. A cancelled write still finishes its frame."""
        ...
