# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Durable ``build.decompose`` handler (M6 task 6.1).

Turns the accepted DESIGN spec into a dependency-ordered work-item graph and
fans it out as ``build.implement`` jobs. The producer's first returned
``WorkItem`` is the walking skeleton by contract -- it must have no
dependencies, matching phase-protocols.md 2.1's "goes first, alone" rule.

The plan is all-or-nothing, end to end (#265):

1. **Judged whole.** Every rule -- unique ids, known dependencies, no cycle,
   every criterion mapped, a dependency-free skeleton -- is checked over the
   whole plan before anything is enqueued, and a plan that breaks any of them
   fails naming every violation. The old fan-out resolved dependencies item by
   item and only noticed a forward dependency on reaching it, with every
   earlier item already committed.
2. **Ordered here.** A sound plan is put into dependency order by the domain
   planner, so a producer that lists a dependent before its dependency is no
   longer an error: the graph, not the list, is what the queue enforces.
3. **Enqueued in one transaction.** ``JobRepository.enqueue_batch`` commits
   every item or none, with each item's key derived from (project, cycle,
   item_id), so a crash mid-fan-out leaves nothing to orphan and a replay
   neither duplicates nor orphans.
4. **Never decomposed twice.** A replay that finds its own fan-out already
   committed (the worker died between the commit and the ack) returns it
   instead of asking the producer again: the producers are models, and a
   second answer would enqueue a second plan beside the first.
"""

from dataclasses import asdict

from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.interfaces import (
    DesignSpecReader,
    WorkPlanProducer,
)
from vibey.application.ports import JobRepository
from vibey.application.worker import Failure, Outcome, Success
from vibey.domain.interfaces.plan_interface import DecompositionPlannerInterface
from vibey.domain.job import FailureClass, idempotency_key
from vibey.domain.phase import Phase
from vibey.domain.plan import DECOMPOSITION_PLANNER, WorkItem
from vibey.domain.worktree import branch_name


class BuildDecomposeHandler:
    _ITEM_KIND = "build.implement"

    def __init__(
        self,
        *,
        specs: DesignSpecReader,
        decomposer: WorkPlanProducer,
        jobs: JobRepository,
        planner: DecompositionPlannerInterface = DECOMPOSITION_PLANNER,
    ) -> None:
        self._specs = specs
        self._decomposer = decomposer
        self._jobs = jobs
        self._planner = planner

    async def handle(self, job: JobRecord) -> Outcome:
        # "build.plan" is the review fast loop-back's spelling of the same
        # work (review_triage_handler.py enqueues it at cycle+1); both kinds
        # decompose the cycle's accepted spec.
        if job.kind not in ("build.decompose", "build.plan"):
            return Failure(FailureClass.VIBEY, "expected build.decompose job")

        fanned_out = await self._fanned_out(job)
        if fanned_out:
            return Success({"work_items": len(fanned_out), "replayed": True})

        spec = await self._specs.load(job.project_id, job.cycle)
        if spec is None:
            return Failure(FailureClass.WORK, "no accepted design spec exists")

        items = await self._decomposer.decompose(spec)
        if not items:
            return Failure(FailureClass.WORK, "decomposition produced no work items")

        criteria_ids = tuple(criterion.criterion_id for criterion in spec.criteria)
        violations = self._planner.violations(
            items, criteria_ids=criteria_ids, walking_skeleton_item_id=items[0].item_id
        )
        if violations:
            return Failure(FailureClass.WORK, "; ".join(violations))

        ordered = self._planner.in_dependency_order(items)
        await self._jobs.enqueue_batch(tuple(self._request(job, item) for item in ordered))
        return Success({"work_items": len(ordered)})

    async def _fanned_out(self, job: JobRecord) -> tuple[JobRecord, ...]:
        """This cycle's fan-out, if an earlier attempt already committed it.

        Only the fan-out's own rows count: a wind-down follow-up or a verify
        repair is a ``build.implement`` of the same cycle too, but its key is
        derived from a different subject, so it never matches its item's key.
        The batch is atomic, so finding any of the fan-out means finding all
        of it.
        """
        existing = await self._jobs.list_for_cycle(
            job.project_id, cycle=job.cycle, kind=self._ITEM_KIND
        )
        return tuple(
            record
            for record in existing
            if record.work_item_id is not None
            and record.idempotency_key == self._item_key(job, record.work_item_id)
        )

    def _request(self, job: JobRecord, item: WorkItem) -> EnqueueRequest:
        return EnqueueRequest(
            project_id=job.project_id,
            cycle=job.cycle,
            phase=Phase.BUILD,
            kind=self._ITEM_KIND,
            idempotency_key=self._item_key(job, item.item_id),
            work_item_id=item.item_id,
            payload={
                "title": item.title,
                "verification": asdict(item.verification),
                # Item branches stack on already-integrated code when
                # any exists (the worktree manager falls back to HEAD
                # before the first integrate): every item branching
                # from the empty base rewrote the same module in
                # parallel and guaranteed add/add merge conflicts.
                "base_ref": branch_name(job.cycle, "integration"),
            },
            requirement={"effort": item.est_effort.name.lower()},
            # By key, not job id: the dependencies are earlier requests of
            # the same batch, whose ids do not exist until it commits.
            depends_on_keys=tuple(self._item_key(job, dep) for dep in item.depends_on),
        )

    def _item_key(self, job: JobRecord, item_id: str) -> str:
        return idempotency_key(job.project_id, job.cycle, self._ITEM_KIND, item_id)


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "DesignSpecReader",
    "WorkPlanProducer",
]
