# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the runner's egress gate declares it needs and gives (sub-doctrine 9.b)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol


class ResolverInterface(Protocol):
    """Turns a name into the addresses it points at."""

    async def resolve(self, host: str, port: int) -> Sequence[str]:
        """Every address `host` resolves to; empty when it does not resolve."""
        ...


class DialerInterface(Protocol):
    """Opens the one outbound connection a request is allowed."""

    async def open(
        self, address: str, port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """A connection to an address already judged allowed."""
        ...


class AccessLogInterface(Protocol):
    """Where the gate says what it let through and what it refused, and why."""

    def allow(self, what: str) -> None:
        """One destination or request that was let through."""
        ...

    def deny(self, what: str, why: str) -> None:
        """One destination or request that was refused, and the reason."""
        ...


class HostPolicyInterface(Protocol):
    """Says which outbound destinations the runner container may reach through the gate."""

    def allows(self, host: str, port: int) -> bool:
        """True only for a declared host pattern on a declared port."""
        ...

    def public(self, address: str) -> bool:
        """True only for a globally routable address: never the host, its LAN or loopback."""
        ...


class RequestPolicyInterface(Protocol):
    """Says which requests may reach the model server on the host."""

    def allows(self, method: str, target: str) -> bool:
        """True only for one of the few endpoints the agent's engine uses."""
        ...
