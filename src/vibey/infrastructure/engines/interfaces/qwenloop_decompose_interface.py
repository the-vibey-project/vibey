# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the sovereign DECOMPOSE provider.

Mirrors `vibey/infrastructure/engines/qwenloop_decompose.py` (ADR-0016). The runtime
seam BuildDecomposeHandler consumes is `WorkPlanProducer` in
`application/interfaces/build.py`; this declares it again beside the class, together
with the grammar the class is judged by. Interfaces declare; they never consume.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from vibey.domain.plan import WorkItem
from vibey.domain.spec import DesignSpec


@runtime_checkable
class QwenloopWorkPlanProducerInterface(Protocol):
    def schema(self, criteria_ids: Sequence[str]) -> dict[str, object]:
        """The JSON schema a decomposition of a spec with these criteria must match."""
        ...

    async def decompose(self, spec: DesignSpec) -> tuple[WorkItem, ...]:
        """A whole, valid plan, or ValueError naming why not -- never part of one."""
        ...
