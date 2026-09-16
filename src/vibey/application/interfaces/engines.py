# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The vendor runner seam. Every *loop CLI shape lives behind this."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import (
    EngineEvent,
    EngineHealthRecord,
    PreflightResult,
    RotationCursor,
    RunHandle,
    RunSpec,
    SnapshotRef,
    StopSummary,
)
from vibey.domain.capacity import CapacityState
from vibey.domain.engine import EngineDescriptor, EngineId, JobRequirement
from vibey.domain.job import FailureClass
from vibey.domain.rotation import Selection


@runtime_checkable
class EngineAdapter(Protocol):
    """infrastructure/engines/ -- the only place vendor CLI shapes exist."""

    @property
    def descriptor(self) -> EngineDescriptor: ...

    async def preflight(self) -> PreflightResult:
        """Runs `<engine> doctor`; classifies auth + availability."""
        ...

    async def start(self, spec: RunSpec) -> RunHandle:
        """Builds argv from descriptor.effort_projection + isolation flags,
        spawns the runner, returns a handle over its run directory."""
        ...

    def tail(self, handle: RunHandle) -> AsyncIterator[EngineEvent]:
        """Streams the runner's events.jsonl, translated into vibey's own
        event vocabulary."""
        ...

    async def send_prompt(self, handle: RunHandle, text: str, *, now: bool) -> None:
        """Writes the runner's control-plane inbox (prompt --now / --at-break)."""
        ...

    async def stop(self, handle: RunHandle) -> StopSummary:
        """Soft-stops the run; collects stop-summary.md and the final
        snapshot."""
        ...

    async def snapshot(self, handle: RunHandle) -> SnapshotRef | None: ...

    def classify(self, raw: Mapping[str, object]) -> CapacityState:
        """Vendor error shape -> vibey's capacity ADT."""
        ...

    def attribute(self, exit_code: int, tail: str) -> FailureClass: ...


@runtime_checkable
class EngineHealthRepository(Protocol):
    async def get(self, project_id: UUID, engine_id: str) -> EngineHealthRecord | None: ...

    async def upsert(self, record: EngineHealthRecord) -> EngineHealthRecord: ...

    async def list_for_project(self, project_id: UUID) -> tuple[EngineHealthRecord, ...]: ...


@runtime_checkable
class RotationCursorRepository(Protocol):
    async def get(self, project_id: UUID, engine_id: EngineId) -> RotationCursor | None: ...

    async def list_for_project(self, project_id: UUID) -> tuple[RotationCursor, ...]: ...

    async def upsert(self, cursor: RotationCursor) -> RotationCursor: ...

    async def update_many(
        self, project_id: UUID, cursors: tuple[RotationCursor, ...]
    ) -> tuple[RotationCursor, ...]: ...

    async def initialize_for_project(
        self, project_id: UUID, engines: tuple[EngineId, ...]
    ) -> tuple[RotationCursor, ...]: ...


# The two seams below are declared here, in the port-family module, rather than in
# mirrored `engine_health_service_interface.py` / `engine_selector_interface.py`
# files. That is a deliberate reading of ADR-0016, not an oversight of it. The ADR
# says in as many words that "the existing `application/interfaces` modules are
# grouped by port family and converge like any other module": this package's
# organising axis is the port family -- everything the rotation seam needs lives in
# `engines.py` beside `EngineAdapter`, `EngineHealthRepository` and
# `RotationCursorRepository` -- and splitting two of its members out into per-module
# mirrors would leave one directory speaking two conventions at once, which is worse
# for a reader than either convention alone. `cli/interfaces/` is greenfield and
# takes the mirrored form; `vibey_gh/interfaces/` likewise. This package converges
# as a unit, in a change whose subject is the convergence, not as a side effect of a
# bug fix. What the ADR actually requires -- that a class have a declared seam, and
# that the seam be a reviewable artifact in a diff -- is satisfied either way, and
# the `_Interface` suffix on the names below keeps the mapping to the class
# mechanical even though the file name does not.


@runtime_checkable
class EngineHealthServiceInterface(Protocol):
    """The contract of `application/engine_health_service.py::EngineHealthService`.

    Every engine's circuit state is written through here, so this is the seam a
    test substitutes to drive a selector without a database.
    """

    async def get_or_create(self, project_id: UUID, engine_id: EngineId) -> EngineHealthRecord: ...

    async def record_preflight(
        self, project_id: UUID, engine_id: EngineId, preflight: PreflightResult
    ) -> EngineHealthRecord:
        """Worker-startup refresh; preserves the conformance verdict."""
        ...

    async def update_from_preflight(
        self,
        project_id: UUID,
        engine_id: EngineId,
        preflight: PreflightResult,
        conformance_ok: bool,
    ) -> EngineHealthRecord:
        """Doctor's verdict: the only caller allowed to grant conformance."""
        ...

    async def record_capacity_rejection(
        self, project_id: UUID, engine_id: EngineId, capacity_state: CapacityState
    ) -> EngineHealthRecord:
        """Opens the circuit and schedules whatever probe the rejection allows.

        `CreditsExhausted` gets `probe_next_at` and never a `resets_at` -- a
        credits balance has no clock, and the database CHECK
        `credits_never_have_a_deadline` enforces it below this seam too.
        """
        ...

    async def record_selection(
        self, project_id: UUID, engine_id: EngineId, cost_usd: float = 0.0
    ) -> EngineHealthRecord: ...

    async def record_success(self, project_id: UUID, engine_id: EngineId) -> EngineHealthRecord: ...

    async def list_for_project(self, project_id: UUID) -> tuple[EngineHealthRecord, ...]: ...


@runtime_checkable
class EngineSelectorInterface(Protocol):
    """The contract of `application/engine_selector.py::EngineSelector`."""

    async def select_engine(
        self,
        project_id: UUID,
        requirement: JobRequirement,
        allow_list: frozenset[EngineId] | None = None,
        cost_aware: bool = False,
        affinity_engine: EngineId | None = None,
    ) -> tuple[EngineId, Selection]:
        """Picks the next engine by SWRR over the eligible, healthy ones.

        Raises `domain.errors.NoEligibleEngine` when none qualify.
        """
        ...
