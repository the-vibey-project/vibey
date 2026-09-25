# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every answer to a human gate takes (`vibey answer`, the operator).

A gate is answered once (`domain/gate_answer.py`): the store writes an answer only while
the gate is open, and records it on the ledger as `GateAnswered` in the same transaction.
This service decides the rest before anything is written:

- **Who answered.** `by` is the name the caller gave (`--by`), or the account that ran
  the command when it gave none; `account`, the operating system's name for that
  account, is recorded beside it whatever the label. `by` is a label for the record, not
  an authority: whoever can run vibey against this database can already answer any gate.
  The record is what makes every answer answerable. A label that cannot be recorded is
  refused (`InvalidActorLabel`).
- **Which request.** A caller that retries names a request id, and a retry with the same
  answer is a no-op; with none, this call is a new request. A request id that cannot be
  stored is refused (`InvalidAnswer`).

Never blocks a worker: answering only ever resumes a parked job (ADR-0009).
"""

from collections.abc import Mapping
from uuid import UUID, uuid4

from vibey.application.dto import GateAnswerOutcome
from vibey.application.interfaces import CallerIdentity
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.domain.actor_label import ACTOR_LABELS
from vibey.domain.gate_answer import GATE_ANSWER_REQUEST_IDS
from vibey.domain.interfaces.actor_label_interface import ActorLabelPolicyInterface
from vibey.domain.interfaces.gate_answer_interface import GateAnswerRequestIdsInterface


class GateAnswerService:
    """Declared by `interfaces/gate_answer.py::GateAnswerServiceInterface`."""

    def __init__(
        self,
        *,
        gates: HumanGateRepository,
        caller: CallerIdentity,
        actors: ActorLabelPolicyInterface = ACTOR_LABELS,
        request_ids: GateAnswerRequestIdsInterface = GATE_ANSWER_REQUEST_IDS,
    ) -> None:
        self._gates = gates
        self._caller = caller
        self._actors = actors
        self._request_ids = request_ids

    async def answer(
        self,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        by: str | None = None,
        request_id: str | None = None,
    ) -> GateAnswerOutcome:
        account = self._caller.current().name
        answered_by = self._actors.resolve(by, account=account)
        request = self._request_ids.checked(request_id) if request_id is not None else str(uuid4())
        return await self._gates.answer_once(
            gate_id,
            answer=answer,
            answered_by=answered_by,
            account=account,
            request_id=request,
        )

    def derived_request_id(self, source: str, gate_id: UUID, answer: Mapping[str, object]) -> str:
        return self._request_ids.derived(source, gate_id, answer)
