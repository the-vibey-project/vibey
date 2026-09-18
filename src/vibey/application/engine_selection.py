# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Per-job engine selection: the first production caller of the rotation
stack (EngineSelector / EngineHealthService), invoked by the composition
root's BUILD factories at dispatch time -- rotation happens only at job
boundaries, never mid-turn (ADR-0007).

Three pieces:

- ``selection_inputs_for_job`` -- pure: derives the JobRequirement,
  forced-rotation exclusion, and WORK-retry affinity from the claimed job's
  own durable state (attempt number, ``assigned_engine`` from the previous
  attempt, the verify job's ``implementer_engine_id``).
- ``SelectingEngineProvider`` -- selects via SWRR, records the selection,
  and durably assigns the engine to the job; ``NoEligibleEngine`` becomes
  ``CapacityDeferred`` so an empty/unhealthy engine table defers the job
  instead of burning an attempt.
- ``RotationRecordingHandler`` -- wraps the constructed handler so the
  selected engine's health record sees the outcome: Success closes the
  circuit, a capacity Defer opens it (which is what makes the *next* claim
  rotate away automatically).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from vibey.application.dto import JobRecord
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.engine_selector import EngineSelector
from vibey.application.interfaces import Clock, EngineAdapter, JobHandler
from vibey.application.ports import JobRepository
from vibey.application.worker import CapacityDeferred, Defer, Outcome, Success
from vibey.domain.capacity import WindowExhausted
from vibey.domain.effort import (
    BUILD_LADDER_EXHAUSTED,
    PHASE_BASE_EFFORT,
    Effort,
    effort_for_attempt,
    forces_rotation,
)
from vibey.domain.engine import EngineId, JobRequirement
from vibey.domain.errors import EscalationExhausted, NoEligibleEngine
from vibey.domain.phase import Phase


@dataclass(frozen=True, slots=True)
class SelectionInputs:
    requirement: JobRequirement
    affinity: EngineId | None
    independence_waived: bool = False
    """True when a ``build.verify`` job's implementer-exclusion was dropped
    because honoring it would have left the configured pool with nobody to
    review at all. The reviewing engine is then the implementer, and
    ``BuildVerifyHandler`` must say so on the ledger -- a non-independent
    diff review is allowed here, never hidden."""


def selection_inputs_for_job(
    job: JobRecord, *, pool: frozenset[EngineId] | None = None
) -> SelectionInputs:
    """Pure derivation of what this job's engine selection must honor.

    Module-level rather than a class (ADR-0016) because it is a pure
    function of one ``JobRecord`` with no collaborators and no state: a
    class would add a constructor and nothing else. It is deliberately the
    *only* definition of the verify-independence rule -- ``BuildVerifyHandler``
    asks it rather than re-deriving, because the two rules disagreeing is
    exactly what deadlocked a single-engine pool (selection produced an
    empty eligible set and deferred forever; the handler hard-failed).

    ``pool`` is the set of engines this worker can actually dispatch to --
    its configured adapters, narrowed by the ``--engines`` allow-list. It is
    configuration, never live health: basing the waiver on health would
    silently drop independence whenever the second engine happened to be
    circuit-open, which is a much worse trade. ``None`` means the pool is
    unknown to this caller, and independence then stays absolute.
    """
    excluded: set[EngineId] = set()
    affinity: EngineId | None = None
    independence_waived = False

    # A durable per-job exclusion list -- the wind-down follow-up's "must
    # not go back to the engine that wound down" constraint rides here.
    raw_excluded = job.requirement.get("excluded_engine_ids")
    if isinstance(raw_excluded, list | tuple):
        excluded.update(EngineId(str(entry)) for entry in raw_excluded)

    if job.kind == "build.verify":
        # The diff review runs at LOW and must come from a different engine
        # than the implementer (phase-protocols.md 2.3).
        implementer = str(job.requirement.get("implementer_engine_id", "") or "")
        if implementer:
            # ...but independence is the default, not an absolute. A pool
            # that cannot supply a second reviewer gets a self-review that
            # says so, because the alternative measured on a one-engine
            # pool was worse in every way: the eligible set went empty,
            # NoEligibleEngine became a CapacityDeferred, and BUILD retried
            # forever with no park, no failure and nothing in the ledger.
            # Phrased as "would this exclusion empty the pool" rather than
            # "is the pool exactly one engine" so it also holds when a
            # durable excluded_engine_ids list has already taken the other
            # candidates -- a rule, not a special case (ADR-0018).
            remaining = None if pool is None else pool - excluded - {EngineId(implementer)}
            if remaining is None or remaining:
                excluded.add(EngineId(implementer))
            else:
                independence_waived = True
        effort = Effort.LOW
    else:
        base = PHASE_BASE_EFFORT[Phase.BUILD]
        attempt = max(job.attempts, 1)
        try:
            effort = effort_for_attempt(base, attempt)
        except EscalationExhausted:
            # Selection must never raise here: the handler owns the
            # exhausted-ladder Park. Select as if HIGH so a needless
            # nack/crash can't preempt the human gate.
            effort = Effort.HIGH
        previous = EngineId(job.assigned_engine) if job.assigned_engine else None
        if attempt > 1 and previous is not None:
            previous_effort = effort_for_attempt(base, min(attempt - 1, BUILD_LADDER_EXHAUSTED))
            if forces_rotation(previous_effort, effort):
                # Tier crossing: the escalated attempt must rotate away.
                excluded.add(previous)
            elif previous not in excluded:
                # Same-tier WORK retry: stickiness (affinity_factor 2.0).
                # An engine the requirement excludes never gets affinity.
                affinity = previous

    return SelectionInputs(
        requirement=JobRequirement(effort=effort, excluded=frozenset(excluded)),
        affinity=affinity,
        independence_waived=independence_waived,
    )


class SelectingEngineProvider:
    """The production ``EngineProvider`` (``application/interfaces/engines.py``)."""

    def __init__(
        self,
        *,
        selector: EngineSelector,
        health: EngineHealthService,
        adapters: Mapping[EngineId, EngineAdapter],
        jobs: JobRepository,
        clock: Clock,
        owner: str,
        allow_list: frozenset[EngineId] | None = None,
        backoff: timedelta = timedelta(minutes=5),
        local_engines: tuple[EngineId, ...] = (),
    ) -> None:
        self._selector = selector
        self._health = health
        self._adapters = adapters
        self._jobs = jobs
        self._clock = clock
        self._owner = owner
        self._backoff = backoff
        self._pool = frozenset(adapters) if allow_list is None else frozenset(adapters) & allow_list
        # Local engines have no cron that records their health, so each selection
        # refreshes theirs first -- only for those this worker can dispatch to.
        self._local_engines = tuple(engine for engine in local_engines if engine in self._pool)

    @property
    def pool(self) -> frozenset[EngineId]:
        """The engines this worker can actually dispatch to: its configured
        adapters narrowed by the ``--engines`` allow-list. Handlers that
        have to apply a pool-shaped rule (``BuildVerifyHandler`` and the
        verify-independence waiver) read it from here, so there is one
        answer to "what engines does this worker have" rather than two."""
        return self._pool

    async def select_for(self, job: JobRecord) -> EngineAdapter:
        inputs = selection_inputs_for_job(job, pool=self._pool)
        for engine_id in self._local_engines:
            # A local engine's `doctor` is its readiness check: the server is up, the
            # model is pulled, and (for claudeloop-local) the model answers a tool
            # call. That is what makes it eligible, and it is refreshed here because
            # nothing else would -- the price ADR-0015 accepted for qwenloop, now paid
            # for every local engine the operator switched on (ADR-0038).
            preflight = await self._adapters[engine_id].preflight()
            await self._health.update_from_preflight(
                job.project_id,
                engine_id,
                preflight,
                conformance_ok=preflight.installed and preflight.auth_ok,
            )
        try:
            # The pool, never None: the selector reads every health row the project
            # has, and a row outlives the switch that created it. Offered an engine
            # this worker has no adapter for -- a local engine switched off since,
            # now *preferred* by tier -- it would defer the job forever.
            engine_id, _selection = await self._selector.select_engine(
                job.project_id,
                inputs.requirement,
                allow_list=self._pool,
                affinity_engine=inputs.affinity,
            )
        except NoEligibleEngine as exc:
            raise CapacityDeferred(self._clock.now() + self._backoff, str(exc)) from exc
        adapter = self._adapters.get(engine_id)
        if adapter is None:
            # Selected from health records but not configured in this worker
            # (e.g. an --engines allow-list narrower than the health table
            # should prevent this; defend anyway).
            raise CapacityDeferred(
                self._clock.now() + self._backoff,
                f"selected engine {engine_id.value} has no configured adapter",
            )
        await self._health.record_selection(job.project_id, engine_id)
        await self._jobs.assign_engine(job.id, owner=self._owner, engine_id=engine_id)
        return adapter


class RotationRecordingHandler:
    """Feeds the selected engine's outcome back into its health record.

    Success closes the circuit; a capacity Defer records a rejection whose
    probe deadline is the Defer's own retry_at (vibey's scheduling state,
    not a fabricated vendor payload) -- opening the circuit is what makes
    the next claim's selection rotate to a different engine.
    """

    def __init__(
        self,
        *,
        inner: JobHandler,
        health: EngineHealthService,
        project_id: UUID,
        engine_id: EngineId,
    ) -> None:
        self._inner = inner
        self._health = health
        self._project_id = project_id
        self._engine_id = engine_id

    async def handle(self, job: JobRecord) -> Outcome:
        outcome = await self._inner.handle(job)
        if isinstance(outcome, Success):
            await self._health.record_success(self._project_id, self._engine_id)
        elif isinstance(outcome, Defer) and outcome.capacity:
            # Only capacity-classed Defers open the circuit. Caught live:
            # verify-repair waits are also Defers, and recording them as
            # rejections opened both engines' circuits and stalled the
            # project on "No engines meet requirements".
            await self._health.record_capacity_rejection(
                self._project_id,
                self._engine_id,
                WindowExhausted(resets_at=outcome.retry_at),
            )
        return outcome
