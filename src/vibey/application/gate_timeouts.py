# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Resolves a waiting gate to its own default, where -- and only where -- its project said so.

The policy is `domain/gate_timeout.py`: per-gate opt-in under `[human_gates]
timeout_defaults`, by the operator's ruling of 2026-09-30 (sub-doctrine 12.d: silence is
not consent; the declaration is). This sweep applies it. It runs from the worker's idle
loop beside the reminder sweep, at most once per interval per scope, and answers through
`GateAnswerService` -- the one path every answer takes -- so each resolution is recorded on
the ledger as `GateAnswered` by `gate-timeout`, under a request id derived from the gate and
the answer, which makes a replayed sweep a no-op.

Nothing is answered on a guess: a project whose declaration cannot be read or honoured, and
a read of open gates that fails, are reported and leave every gate waiting (10.g).
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Final
from uuid import UUID

from vibey.application.dto import (
    GateTimeoutReport,
    HumanGateRecord,
    ProjectRecord,
    ResolvedGate,
)
from vibey.application.interfaces.gate_answer import GateAnswerServiceInterface
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.projects import ProjectReader
from vibey.application.interfaces.system import Clock
from vibey.domain.config import ConfigError
from vibey.domain.gate_notice import DEFAULT_SWEEP_INTERVAL_SECONDS
from vibey.domain.gate_timeout import GateTimeoutPolicy

GATE_TIMEOUT_ACTOR: Final = "gate-timeout"
"""Who the ledger says answered a gate that resolved to its default."""

REQUEST_SOURCE: Final = "gate-timeout"


class GateTimeoutSweep:
    """Declared by `interfaces/gate_timeouts.py::GateTimeoutSweepInterface`."""

    def __init__(
        self,
        *,
        gates: HumanGateRepository,
        projects: ProjectReader,
        answers: GateAnswerServiceInterface,
        clock: Clock,
        logger: Logger,
        interval_seconds: int = DEFAULT_SWEEP_INTERVAL_SECONDS,
    ) -> None:
        self._gates = gates
        self._projects = projects
        self._answers = answers
        self._clock = clock
        self._log = logger
        self._interval = interval_seconds
        self._last: dict[UUID | None, datetime] = {}

    async def run_if_due(self, project_id: UUID | None) -> GateTimeoutReport | None:
        now = self._clock.now()
        last = self._last.get(project_id)
        if last is not None and (now - last).total_seconds() < self._interval:
            return None
        # Claimed before the first await, so parallel drive loops cannot both find it due.
        self._last[project_id] = now
        return await self.run(project_id)

    async def run(self, project_id: UUID | None = None) -> GateTimeoutReport:
        now = self._clock.now()
        try:
            gates, projects = await self._read(project_id)
        except Exception as exc:
            report = GateTimeoutReport(project_id=project_id, refused=(f"open gates: {exc}",))
            self._log.warning("gate.timeout_unreadable", source=report.refused[0])
            return report
        named = {project.project_id: project for project in projects}
        grouped: dict[UUID, list[HumanGateRecord]] = defaultdict(list)
        for gate in gates:
            if gate.project_id in named:
                grouped[gate.project_id].append(gate)
        resolved: list[ResolvedGate] = []
        refused: list[str] = []
        failed: list[str] = []
        for pid, waiting in grouped.items():
            project = named[pid]
            try:
                policy = GateTimeoutPolicy.from_config(project.config)
            except ConfigError as exc:
                refused.append(f"project {project.name}: {exc}")
                self._log.warning(
                    "gate.timeout_config_invalid", project_id=str(pid), error=str(exc)
                )
                continue
            for gate in waiting:
                waited = max((now - gate.raised_at).total_seconds(), 0.0)
                answer = policy.resolution(
                    kind=gate.kind, default_answer=gate.default_answer, waited_seconds=waited
                )
                if answer is None:
                    continue
                try:
                    await self._answers.answer(
                        gate.gate_id,
                        answer,
                        by=GATE_TIMEOUT_ACTOR,
                        request_id=self._answers.derived_request_id(
                            REQUEST_SOURCE, gate.gate_id, answer
                        ),
                    )
                except Exception as exc:
                    failed.append(f"gate {gate.gate_id} ({gate.kind}): {exc}")
                    self._log.warning(
                        "gate.timeout_answer_failed",
                        project_id=str(pid),
                        gate_id=str(gate.gate_id),
                        gate_kind=gate.kind,
                        error=str(exc),
                    )
                    continue
                resolved.append(
                    ResolvedGate(
                        project_id=pid,
                        gate_id=gate.gate_id,
                        gate_kind=gate.kind,
                        answer=answer,
                        waited_seconds=waited,
                    )
                )
                self._log.info(
                    "gate.resolved_by_timeout",
                    project_id=str(pid),
                    gate_id=str(gate.gate_id),
                    gate_kind=gate.kind,
                    answer=answer,
                    waited_seconds=round(waited),
                )
        return GateTimeoutReport(
            project_id=project_id,
            waiting=sum(len(waiting) for waiting in grouped.values()),
            resolved=tuple(resolved),
            refused=tuple(refused),
            failed=tuple(failed),
        )

    async def _read(
        self, project_id: UUID | None
    ) -> tuple[Sequence[HumanGateRecord], Sequence[ProjectRecord]]:
        if project_id is None:
            return await self._gates.open_all(), await self._projects.list_all()
        gates = await self._gates.open_for_project(project_id)
        project = await self._projects.get(project_id)
        return gates, (project,) if project is not None else ()
