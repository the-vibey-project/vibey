# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the PostgreSQL side of human gates (ADR-0009).

Mirrors `vibey/infrastructure/db/human_gate_repository.py` (ADR-0016). Interfaces
declare; they never consume. The DTO and draft types are imported under TYPE_CHECKING
only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.gates import HumanGateRepository

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.application.dto import HumanGateRecord, ProjectRecord
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class GateAnsweredDraftBuilderInterface(Protocol):
    """Builds the `GateAnswered` ledger draft for one answered gate."""

    def build(
        self,
        project: ProjectRecord,
        gate: HumanGateRecord,
        *,
        account: str | None,
        at: datetime,
    ) -> LedgerEventDraft:
        """Filed under the project's cycle and phase, `trusted`, with no engine and no
        job of its own. Raises `WrongPhase` for a phase this vibey does not know."""
        ...


@runtime_checkable
class PostgresHumanGateRepositoryInterface(HumanGateRepository, Protocol):
    """Raises gates, and answers each once: a compare-and-set on `answered_at IS NULL`
    and its `GateAnswered` event in one transaction."""
