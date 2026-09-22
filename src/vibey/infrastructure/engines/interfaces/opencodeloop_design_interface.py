# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the sovereign/local OpenCode DESIGN provider.

Mirrors `vibey/infrastructure/engines/opencodeloop_design.py` (ADR-0016). The runtime
seam the DESIGN handlers consume is `DesignProvider` in `application/interfaces/design.py`;
this declares it again beside the class, together with the refusal it owes a caller.
Interfaces declare; they never consume.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from vibey.application.design import DesignEvent, DesignStage, QuestionBatch, ResearchResult
from vibey.domain.engine import EngineId
from vibey.domain.spec import DesignSpec


@runtime_checkable
class OpenCodeLoopDesignProviderInterface(Protocol):
    engine_id: EngineId | None

    async def batch(
        self, stage: DesignStage, prior_events: Sequence[DesignEvent]
    ) -> QuestionBatch: ...

    async def research(self, topic: str) -> ResearchResult: ...

    async def synthesize(self, events: Sequence[DesignEvent]) -> DesignSpec: ...
