"""Shared interaction contract.

This module defines a minimal interaction interface that is used by a conversation
handler and other surfaces.  The interface is intentionally small – it only
exposes a :meth:`send` coroutine that accepts a message string and returns a
response string.

The corresponding in‑memory implementation is a stub that simply echoes the
message back prefixed with ``"Echo: "``.

The goal of this file is to provide a shared contract that can be imported by
different parts of the application.  It is a very small part of the larger
#85 split, but gives tests a stable slice that can be exercised.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class InteractionInterface(ABC):
    """A protocol for sending a message and receiving a reply.
    """

    @abstractmethod
    async def send(self, message: str) -> str:
        """Send *message* and return a response.
        """
        raise NotImplementedError


class InMemoryInteractionFake(InteractionInterface):
    """A very small in‑memory fake that echoes messages.
    """

    async def send(self, message: str) -> str:  # pragma: no cover - trivial
        return f"Echo: {message}"


__all__ = [
    "InteractionInterface",
    "InMemoryInteractionFake",
]
