# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every answer to a gate takes (`application/gate_answer.py`)."""

from uuid import UUID, uuid4

import pytest

from vibey.application.dto import HumanGateRequest
from vibey.application.gate_answer import GateAnswerService
from vibey.application.interfaces import GateAnswerServiceInterface
from vibey.domain.errors import GateAlreadyAnswered, InvalidActorLabel, InvalidAnswer, UnknownGate
from vibey.domain.queue_priority import Caller

from .fakes import FakeHumanGateRepository


class _Caller:
    def current(self) -> Caller:
        return Caller(uid=501, name="adam")


async def _open_gate(gates: FakeHumanGateRepository) -> UUID:
    raised = await gates.raise_gate(
        uuid4(), uuid4(), HumanGateRequest(kind="approval", prompt="go?")
    )
    return raised.gate_id


def _service(gates: FakeHumanGateRepository) -> GateAnswerService:
    return GateAnswerService(gates=gates, caller=_Caller())


def test_the_service_satisfies_its_interface() -> None:
    assert isinstance(_service(FakeHumanGateRepository()), GateAnswerServiceInterface)


async def test_an_answer_records_the_account_when_no_one_is_named() -> None:
    gates = FakeHumanGateRepository()
    gate_id = await _open_gate(gates)

    outcome = await _service(gates).answer(gate_id, {"choice": "yes"})

    assert not outcome.replayed
    assert outcome.record.answered_by == "adam"
    assert outcome.record.answer == {"choice": "yes"}
    assert outcome.record.answer_request_id is not None
    assert gates.accounts[gate_id] == "adam"


async def test_a_named_answerer_is_recorded_with_the_account_beside_it() -> None:
    gates = FakeHumanGateRepository()
    gate_id = await _open_gate(gates)

    outcome = await _service(gates).answer(gate_id, {"choice": "yes"}, by=" vibey-vscode ")

    assert outcome.record.answered_by == "vibey-vscode"
    assert gates.accounts[gate_id] == "adam"


async def test_the_same_request_again_is_a_no_op_success() -> None:
    gates = FakeHumanGateRepository()
    gate_id = await _open_gate(gates)
    service = _service(gates)

    first = await service.answer(gate_id, {"choice": "yes"}, request_id="r-1")
    again = await service.answer(gate_id, {"choice": "yes"}, request_id="r-1")

    assert not first.replayed
    assert again.replayed
    assert again.record == first.record


async def test_a_second_request_is_refused_and_the_first_answer_stands() -> None:
    gates = FakeHumanGateRepository()
    gate_id = await _open_gate(gates)
    service = _service(gates)
    await service.answer(gate_id, {"choice": "yes"})

    with pytest.raises(GateAlreadyAnswered) as refused:
        await service.answer(gate_id, {"choice": "no"})

    assert refused.value.answered_by == "adam"
    assert not refused.value.same_request
    stored = next(g for g in gates.raised if g.gate_id == gate_id)
    assert stored.answer == {"choice": "yes"}


async def test_the_same_request_id_with_a_different_answer_is_refused() -> None:
    gates = FakeHumanGateRepository()
    gate_id = await _open_gate(gates)
    service = _service(gates)
    await service.answer(gate_id, {"choice": "yes"}, request_id="r-1")

    with pytest.raises(GateAlreadyAnswered, match="already used for a different answer") as refused:
        await service.answer(gate_id, {"choice": "no"}, request_id="r-1")

    assert refused.value.same_request


async def test_bad_labels_and_request_ids_are_refused_before_anything_is_written() -> None:
    gates = FakeHumanGateRepository()
    gate_id = await _open_gate(gates)
    service = _service(gates)

    with pytest.raises(InvalidActorLabel):
        await service.answer(gate_id, {"choice": "yes"}, by="\n")
    with pytest.raises(InvalidAnswer):
        await service.answer(gate_id, {"choice": "yes"}, request_id="has space")

    assert "answer" not in gates.calls


async def test_an_unknown_gate_is_refused() -> None:
    with pytest.raises(UnknownGate):
        await _service(FakeHumanGateRepository()).answer(uuid4(), {"choice": "yes"})


def test_a_derived_request_id_is_the_domain_policy_s() -> None:
    gate_id = uuid4()
    service = _service(FakeHumanGateRepository())
    assert service.derived_request_id("operator", gate_id, {"a": 1}) == service.derived_request_id(
        "operator", gate_id, {"a": 1}
    )
