# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind identifying one request that answers a gate.

Mirrors `vibey/domain/gate_answer.py` (ADR-0016). Interfaces declare; they never consume.
The types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID


@runtime_checkable
class GateAnswerRequestIdsInterface(Protocol):
    """Checks and derives the id of one answering request."""

    def checked(self, request_id: str) -> str:
        """`request_id` as given, or `InvalidAnswer` when it cannot be stored."""
        ...

    def derived(self, source: str, gate_id: UUID, answer: Mapping[str, object]) -> str:
        """The one request id `source` uses for this answer to this gate, every time."""
        ...
