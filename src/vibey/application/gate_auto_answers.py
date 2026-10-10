# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Answers the gates a worker was told it may answer, and no others.

The policy is `domain/gate_auto_answer.py`. Unlike the timeout sweep (`gate_timeouts.py`),
which acts on a declaration the repository made in advance, this acts on the operator's own
`vibey worker --auto-answer`, given for that one worker: the consent is the flag, so no
silence is read as consent (sub-doctrine 12.d). It answers through `GateAnswerService`, the
one path every answer takes, so each is recorded on the ledger as `GateAnswered` by
`auto-answer`, under a request id derived from the gate and the answer, which makes a replayed
sweep a no-op.

Nothing is answered on a guess: a read of open gates that fails is reported and leaves every
gate waiting (10.g). The worker gives at most `policy.limit` answers and then says so once.
"""

import asyncio
from typing import Final
from uuid import UUID

from vibey.application.dto import AutoAnsweredGate, GateAutoAnswerReport
from vibey.application.interfaces.gate_answer import GateAnswerServiceInterface
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.system import Clock
from vibey.domain.gate_auto_answer import GateAutoAnswerPolicy

GATE_AUTO_ANSWER_ACTOR: Final = "auto-answer"
"""Who the ledger says answered a gate this worker answered."""


class GateAutoAnswerSweep:
    """Declared by `interfaces/gate_auto_answers.py::GateAutoAnswerSweepInterface`."""

    def __init__(
        self,
        *,
        gates: HumanGateRepository,
        answers: GateAnswerServiceInterface,
        policy: GateAutoAnswerPolicy,
        clock: Clock,
        logger: Logger,
    ) -> None:
        self._gates = gates
        self._answers = answers
        self._policy = policy
        self._clock = clock
        self._log = logger
        self._given = 0
        # Parallel drive loops share one sweep: one at a time, so two cannot both answer a
        # gate and spend the limit twice.
        self._lock = asyncio.Lock()

    async def run(self, project_id: UUID | None = None) -> GateAutoAnswerReport:
        async with self._lock:
            if self._given >= self._policy.limit:
                return GateAutoAnswerReport(project_id=project_id)
            return await self._sweep(project_id)

    async def _sweep(self, project_id: UUID | None) -> GateAutoAnswerReport:
        now = self._clock.now()
        try:
            if project_id is None:
                open_gates = await self._gates.open_all()
            else:
                open_gates = await self._gates.open_for_project(project_id)
        except Exception as exc:
            self._log.warning("gate.auto_answer_unreadable", source=str(exc))
            return GateAutoAnswerReport(project_id=project_id, refused=(f"open gates: {exc}",))
        answered: list[AutoAnsweredGate] = []
        left: list[str] = []
        failed: list[str] = []
        for gate in sorted(open_gates, key=lambda g: g.raised_at):
            answer = self._policy.answer_for(gate.kind)
            if answer is None:
                left.append(f"{gate.kind} gate {gate.gate_id}")
                continue
            if self._given >= self._policy.limit:
                break
            try:
                await self._answers.answer(
                    gate.gate_id,
                    answer,
                    by=GATE_AUTO_ANSWER_ACTOR,
                    request_id=self._answers.derived_request_id(
                        GATE_AUTO_ANSWER_ACTOR, gate.gate_id, answer
                    ),
                )
            except Exception as exc:
                failed.append(f"gate {gate.gate_id} ({gate.kind}): {exc}")
                self._log.warning(
                    "gate.auto_answer_failed",
                    project_id=str(gate.project_id),
                    gate_id=str(gate.gate_id),
                    gate_kind=gate.kind,
                    error=str(exc),
                )
                continue
            self._given += 1
            waited = max((now - gate.raised_at).total_seconds(), 0.0)
            answered.append(
                AutoAnsweredGate(
                    project_id=gate.project_id,
                    gate_id=gate.gate_id,
                    gate_kind=gate.kind,
                    answer=answer,
                    waited_seconds=waited,
                )
            )
            self._log.info(
                "gate.auto_answered",
                project_id=str(gate.project_id),
                gate_id=str(gate.gate_id),
                gate_kind=gate.kind,
                answer=answer,
                given=self._given,
                limit=self._policy.limit,
            )
        return GateAutoAnswerReport(
            project_id=project_id,
            waiting=len(open_gates),
            answered=tuple(answered),
            left=tuple(left),
            failed=tuple(failed),
            limit_reached=bool(answered) and self._given >= self._policy.limit,
        )
