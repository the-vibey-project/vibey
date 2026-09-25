# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Answering a gate's seam: the one service every entry point answers through.

Mirrors `vibey/application/gate_answer.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import GateAnswerOutcome


@runtime_checkable
class GateAnswerServiceInterface(Protocol):
    """Answers a gate once, recording who answered and from which account."""

    async def answer(
        self,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        by: str | None = None,
        request_id: str | None = None,
    ) -> GateAnswerOutcome:
        """Answers `gate_id` as `by` (the account when `None`), recording the account
        beside it. With `request_id` a retry of the same answer is a no-op
        (`replayed`); without one this call is a new request. Raises `InvalidActorLabel`
        or `InvalidAnswer` before anything is written, `UnknownGate` for no such gate,
        and `GateAlreadyAnswered` when another request answered it first."""
        ...

    def derived_request_id(self, source: str, gate_id: UUID, answer: Mapping[str, object]) -> str:
        """The request id `source` uses every time it applies `answer` to `gate_id`."""
        ...
