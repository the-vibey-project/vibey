# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Engine selector: the first production caller of domain/rotation.select().

Combines engine health records, rotation cursor state, and job requirements
to select the next engine using SWRR. Updates the rotation cursor atomically.

Tiers come first: the eligible engines of the most-preferred tier (LOCAL before
PAID, sub-doctrine 8.a) are the only ones offered to SWRR, so a paid engine is
the fallback when no local engine can take the job (ADR-0038).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from vibey.application.dto import EngineHealthRecord, RotationCursor
from vibey.application.interfaces.engines import (
    EngineHealthServiceInterface,
    RotationCursorRepository,
)
from vibey.domain.capacity import Available
from vibey.domain.circuit import CIRCUIT_STATE_PARSER, Circuit, CircuitState
from vibey.domain.engine import EngineDescriptor, EngineId, JobRequirement
from vibey.domain.errors import NoEligibleEngine
from vibey.domain.rotation import (
    Candidate,
    EngineRuntime,
    Selection,
    eligible,
    fidelity_factor,
    health_factor,
    preferred_tier,
    select,
)

# Authentication TTL from architecture doc
AUTH_TTL = timedelta(hours=24)


class EngineSelector:
    """Selects engines using SWRR over eligible, healthy engines.

    Declared by `interfaces/engines.py::EngineSelectorInterface`, and it takes
    `EngineHealthServiceInterface` rather than the concrete service so a test
    substitutes the health seam instead of patching an import (ADR-0016). Both
    seams are declared in the port-family module `interfaces/engines.py`; the
    reason that package keeps the family-grouped form is written there.
    """

    def __init__(
        self,
        health_service: EngineHealthServiceInterface,
        cursor_repository: RotationCursorRepository,
        descriptors: dict[EngineId, EngineDescriptor],
    ) -> None:
        self._health_service = health_service
        self._cursor_repository = cursor_repository
        self._descriptors = descriptors

    def _circuit_state(self, record: EngineHealthRecord, *, now: datetime) -> CircuitState | None:
        """The stored circuit, half-opened once its probe time has arrived; None
        for a circuit state a newer vibey added (vibey#287).

        None means "not selectable here": this selector cannot tell whether a
        circuit state it does not know admits a run, and selecting an engine whose
        circuit it cannot read would be guessing. It never raises on the row.

        An OPEN circuit is never selected, and only a *selected* run can
        succeed and close it, so whatever half-opens the circuit is the only
        way back. Half-open is selectable at reduced weight --
        domain/rotation.py's 0.25 -- which is exactly a probe.

        Both scheduled times count, and the earliest one wins. `resets_at` is
        a rate-limit window's own deadline; `probe_next_at` is the backoff
        EngineHealthService writes for a rejection that has no deadline --
        `CreditsExhausted` above all, which deliberately carries no
        `resets_at` and never will, because a credits balance has no clock.
        Reading only `resets_at` left a credit-exhausted engine excluded for
        the rest of the project unless a human edited `engine_health` by hand.

        `AuthenticationFailed` is the one rejection that gets neither time,
        and that is the decision, not an oversight: no amount of waiting
        fixes a credential, so inventing a deadline for it would be the same
        error as giving `CreditsExhausted` a `resets_at`. It stays OPEN --
        visible as `circuit=open, capacity_state=AuthenticationFailed` in
        `vibey status` and the dashboard, never silently dropped -- until a
        human re-authenticates. EngineHealthService half-opens it on the
        first preflight whose auth succeeds, so the human's fix is the probe
        trigger and no hand-edited row is needed there either.
        """
        state = CIRCUIT_STATE_PARSER.known(str(record.circuit))
        if state is not CircuitState.OPEN:
            return state
        scheduled = tuple(at for at in (record.resets_at, record.probe_next_at) if at is not None)
        if scheduled and now >= min(scheduled):
            return CircuitState.HALF_OPEN
        return state

    @staticmethod
    def _known_cursors(cursors: tuple[RotationCursor, ...]) -> dict[EngineId, RotationCursor]:
        return {c.engine_id: c for c in cursors if isinstance(c.engine_id, EngineId)}

    async def select_engine(
        self,
        project_id: UUID,
        requirement: JobRequirement,
        allow_list: frozenset[EngineId] | None = None,
        cost_aware: bool = False,
        affinity_engine: EngineId | None = None,
    ) -> tuple[EngineId, Selection]:
        """Select next engine using SWRR.

        Returns (engine_id, Selection with updated cursor state).
        Raises NoEligibleEngine if no engines meet requirements.
        """
        # Get health records
        health_records = await self._health_service.list_for_project(project_id)

        # Build EngineRuntime objects
        now = datetime.now(UTC)
        runtimes = []
        for record in health_records:
            # A health row a newer vibey wrote for an engine this one does not know
            # (vibey#287; #281's `claudeloop-local` is the first) is not a candidate:
            # this worker has no descriptor and no adapter for it.
            engine_id = record.engine_id
            if not isinstance(engine_id, EngineId):
                continue
            descriptor = self._descriptors.get(engine_id)
            if descriptor is None:
                continue
            state = self._circuit_state(record, now=now)
            if state is None:
                continue

            # Check auth TTL
            auth_valid = record.auth_ok_at is not None and (now - record.auth_ok_at) < AUTH_TTL

            circuit = Circuit(
                state=state,
                capacity=Available(),
                probe=None,
                consecutive_failures=record.consecutive_fail,
                ewma_failure=record.ewma_failure,
            )

            runtimes.append(
                EngineRuntime(
                    engine_id=engine_id,
                    descriptor=descriptor,
                    circuit=circuit,
                    installed=record.installed,
                    conformance_ok=record.conformance_ok,
                    auth_valid=auth_valid,
                )
            )

        # Filter to eligible engines
        eligible_runtimes = eligible(runtimes, requirement=requirement, allow_list=allow_list)
        if not eligible_runtimes:
            raise NoEligibleEngine(f"No engines meet requirements for project {project_id}")

        # Get rotation cursors. A cursor a newer vibey keeps for an engine this one
        # does not know (vibey#287) is left out, so it neither counts toward "every
        # eligible engine has one" nor gets rewritten below.
        cursor_map = self._known_cursors(await self._cursor_repository.list_for_project(project_id))

        # Initialize cursors for any missing engines
        if len(cursor_map) < len(eligible_runtimes):
            all_engine_ids = tuple(self._descriptors.keys())
            await self._cursor_repository.initialize_for_project(project_id, all_engine_ids)
            cursor_map = self._known_cursors(
                await self._cursor_repository.list_for_project(project_id)
            )

        # Build candidates
        candidates: list[Candidate] = []
        for runtime in eligible_runtimes:
            cursor = cursor_map.get(runtime.engine_id)
            if cursor is None:
                # Shouldn't happen after initialization, but handle gracefully
                cursor = RotationCursor(
                    project_id=project_id,
                    engine_id=runtime.engine_id,
                    current=0,
                    order=len(candidates),
                )

            # Calculate factors
            h_factor = health_factor(runtime.circuit)
            f_factor = fidelity_factor(runtime.descriptor, requirement.effort)
            c_factor = 1.0  # Cost factor disabled by default
            a_factor = 2.0 if affinity_engine == runtime.engine_id else 1.0

            candidates.append(
                Candidate(
                    engine_id=runtime.engine_id,
                    base_weight=runtime.descriptor.base_weight,
                    current=cursor.current,
                    order=cursor.order,
                    health_factor=h_factor,
                    fidelity_factor=f_factor,
                    cost_factor=c_factor,
                    affinity_factor=a_factor,
                    tier=runtime.descriptor.tier,
                )
            )

        # Sovereign before paid (sub-doctrine 8.a, ADR-0038): SWRR runs within the
        # most-preferred tier that can win a round. This replaced a hard-coded
        # "qwenloop only when nothing paid is eligible" filter -- the standby rule
        # ADR-0015 recorded as an open tension with 8.a.
        selection = select(preferred_tier(candidates))

        # Update rotation cursors
        updated_cursors = tuple(
            RotationCursor(
                project_id=project_id,
                engine_id=c.engine_id,
                current=c.current,
                order=c.order,
            )
            for c in selection.candidates
        )
        await self._cursor_repository.update_many(project_id, updated_cursors)

        return selection.engine_id, selection


__all__ = ["EngineSelector"]
