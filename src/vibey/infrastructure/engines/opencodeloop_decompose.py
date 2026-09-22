# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Live OpenCodeLoop implementation of the WorkPlanProducer port.

Modeled on ClaudeLoopWorkPlanProducer: model text crosses this boundary only
through strict JSON decoders, and a structurally invalid decomposition
fails fast here (with the violation named) rather than surviving to
confuse the handler -- BuildDecomposeHandler re-validates independently,
but a producer that ships known-bad output would waste a whole job attempt
learning what this module can already see.

The decoders are `design_json.WorkPlanDecoder`, shared with the sovereign
producer, so both refuse a malformed plan for the same reasons.
"""

import json
from pathlib import Path
from uuid import uuid4

from vibey.application.dto import RunSpec
from vibey.domain.effort import Effort
from vibey.domain.engine import IsolationLevel
from vibey.domain.plan import WorkItem
from vibey.domain.spec import DesignSpec
from vibey.infrastructure.engines.design_json import WorkPlanDecoder
from vibey.infrastructure.engines.interfaces.design_json_interface import (
    WorkPlanDecoderInterface,
)
from vibey.infrastructure.engines.opencodeloop_design import _object
from vibey.infrastructure.interfaces import BoundedOpenCodeLoop


class OpenCodeLoopWorkPlanProducer:
    def __init__(
        self,
        *,
        process: BoundedOpenCodeLoop,
        worktree_path: Path,
        decoder: WorkPlanDecoderInterface | None = None,
    ) -> None:
        self._process = process
        self._worktree_path = worktree_path
        self._decoder = decoder if decoder is not None else WorkPlanDecoder()

    async def decompose(self, spec: DesignSpec) -> tuple[WorkItem, ...]:
        prompt = (
            "Decompose this accepted design spec into a dependency-ordered work-item graph. "
            "The FIRST item must be the walking skeleton, with no dependencies. Every "
            "acceptance criterion must appear in at least one item's acceptance_ids, and "
            "every item's verification.criteria_checked must be non-empty. Items must be "
            "ordered so every dependency precedes its dependents. Every item_id must be "
            'lowercase alphanumeric with hyphens (e.g. "ws", "cli-parsing") -- it '
            "becomes a git branch name. Items that will modify the same file MUST be "
            "chained via depends_on (they run in parallel branches otherwise and their "
            "merges conflict). Every verification command must be self-contained and "
            "pass in a clean checkout with nothing installed (no pip install, no "
            "network); prefer one pytest suite under tests/ shared by all items over "
            "inventing per-item test styles. Do not inspect files; "
            "answer immediately in this first turn. Return only JSON with shape "
            '{"items":[{"item_id":str,"title":str,"acceptance_ids":[str],'
            '"depends_on":[str],"est_effort":"trivial|low|standard|high|max",'
            '"verification":{"commands":[str],"criteria_checked":[str]}}]}.\n'
            f"Spec: {json.dumps(self._decoder.spec_json(spec), default=str)}"
        )
        result = await self._process.run(
            RunSpec(
                run_id=uuid4(),
                worktree_path=self._worktree_path,
                prompt=prompt,
                effort=Effort.STANDARD,
                isolation=IsolationLevel.WORKTREE,
            )
        )
        items = self._decoder.items(_object(result.response).get("items"))
        self._decoder.require_unique(items)
        self._decoder.require_valid(
            items, [criterion.criterion_id for criterion in spec.criteria], strict=True
        )
        return items
