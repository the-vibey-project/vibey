# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Phase 1 collaborators: interviewing, researching, and synthesising a spec."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.design import (
    DesignEvent,
    DesignStage,
    QuestionBatch,
    ResearchResult,
)
from vibey.domain.engine import EngineId
from vibey.domain.spec import DesignSpec


@runtime_checkable
class DesignProvider(Protocol):
    @property
    def engine_id(self) -> EngineId | None:
        """Which engine the ledger must name for work this provider does.

        The ledger is append-only and is the project's evidence, so the
        attributed actor has to be the one that actually ran: a sovereign
        DESIGN on qwenloop may not be recorded as claudeloop. Each provider
        declares its own identity here -- one declaration beside the
        implementation, rather than a literal repeated at every wiring site --
        and the composition root reads it. `None` is the truthful answer for a
        provider that is not an engine at all (the scripted one): the ledger's
        `engine_id` is nullable precisely so an event can decline to name an
        actor rather than borrow someone else's.
        """

    async def batch(
        self, stage: DesignStage, prior_events: Sequence[DesignEvent]
    ) -> QuestionBatch: ...

    async def research(self, topic: str) -> ResearchResult: ...

    async def synthesize(self, events: Sequence[DesignEvent]) -> DesignSpec: ...


@runtime_checkable
class DesignQuestionProvider(Protocol):
    async def batch(
        self, stage: DesignStage, prior_events: Sequence[DesignEvent]
    ) -> QuestionBatch: ...


@runtime_checkable
class DesignSpecReader(Protocol):
    """Read-only access to an accepted spec, shared by decompose and review."""

    async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None: ...


@runtime_checkable
class DesignSpecRepository(Protocol):
    async def save(self, project_id: UUID, cycle: int, spec: DesignSpec) -> None: ...

    async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None: ...

    async def publish(self, project_id: UUID, cycle: int, spec: DesignSpec) -> None: ...


@runtime_checkable
class ResearchProvider(Protocol):
    async def research(self, topic: str) -> ResearchResult: ...


@runtime_checkable
class SpecSynthesizer(Protocol):
    async def synthesize(self, events: Sequence[DesignEvent]) -> DesignSpec: ...
