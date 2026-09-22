# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the sovereign/local OpenCode DECOMPOSE provider.

Mirrors `vibey/infrastructure/engines/opencodeloop_decompose.py` (ADR-0016). The runtime
seam BuildDecomposeHandler consumes is `WorkPlanProducer` in
`application/interfaces/build.py`; this declares it again beside the class.
Interfaces declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.domain.plan import WorkItem
from vibey.domain.spec import DesignSpec


@runtime_checkable
class OpenCodeLoopWorkPlanProducerInterface(Protocol):
    async def decompose(self, spec: DesignSpec) -> tuple[WorkItem, ...]: ...
