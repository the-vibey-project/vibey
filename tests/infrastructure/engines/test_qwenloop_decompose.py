# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign DECOMPOSE provider (8.a): BUILD's plan without paid credentials."""

import copy
import json
from collections.abc import Mapping

import pytest

from vibey.domain.effort import Effort
from vibey.domain.spec import AcceptanceCriterion, DesignSpec
from vibey.infrastructure.engines.design_json import WorkPlanDecoder
from vibey.infrastructure.engines.interfaces import (
    OllamaChatClientInterface,
    QwenloopWorkPlanProducerInterface,
    WorkPlanDecoderInterface,
)
from vibey.infrastructure.engines.qwenloop_decompose import (
    DECOMPOSE_SYSTEM,
    QwenloopWorkPlanProducer,
)


class FakeChat:
    """The shared client's seam, answering with a fixed decomposition."""

    def __init__(self, answer: dict[str, object]) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str, dict[str, object]]] = []

    @property
    def base_url(self) -> str:
        return "http://fake:11434"

    @property
    def model(self) -> str:
        return "fake"

    def context_window(self, prompt_chars: int) -> int:
        return 4096

    async def ask(self, system: str, user: str, schema: Mapping[str, object]) -> dict[str, object]:
        self.asked.append((system, user, dict(schema)))
        return self.answer


def _criterion(criterion_id: str) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id=criterion_id,
        given="a name",
        when="greet runs",
        then="a greeting returns",
        fit="exact match",
    )


def _spec(*criteria_ids: str) -> DesignSpec:
    return DesignSpec(
        objective="a greeter",
        constraints=(),
        non_goals=(),
        criteria=tuple(_criterion(c) for c in criteria_ids),
        nfrs=(),
        walking_skeleton="greet() end to end",
    )


def _item(
    item_id: str,
    *,
    acceptance: list[str],
    depends_on: list[str] | None = None,
    commands: list[str] | None = None,
    checked: list[str] | None = None,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "title": f"do {item_id}",
        "acceptance_ids": acceptance,
        "depends_on": depends_on or [],
        "est_effort": "low",
        "files_touched_hint": ["greeter.py"],
        "verification": {
            "commands": ["python -m pytest -q tests"] if commands is None else commands,
            "criteria_checked": acceptance if checked is None else checked,
        },
    }


VALID = {
    "items": [
        _item("WS", acceptance=["AC-1"]),
        _item("cli-parsing", acceptance=["AC-2"], depends_on=["WS"]),
    ]
}


def _producer(answer: dict[str, object]) -> tuple[QwenloopWorkPlanProducer, FakeChat]:
    chat = FakeChat(answer)
    return QwenloopWorkPlanProducer(chat=chat), chat


@pytest.mark.asyncio
async def test_a_valid_plan_decodes_whole() -> None:
    producer, chat = _producer(VALID)

    items = await producer.decompose(_spec("AC-1", "AC-2"))

    # Ids are normalised onto the worktree shape on the way in, dependencies with them.
    assert [item.item_id for item in items] == ["ws", "cli-parsing"]
    assert items[1].depends_on == ("ws",)
    assert items[0].est_effort is Effort.LOW
    assert items[0].files_touched_hint == ("greeter.py",)
    # The point of the provider: every item carries a command its verify gate will run.
    assert all(item.verification.commands for item in items)
    assert items[1].verification.criteria_checked == ("AC-2",)
    ((system, user, _schema),) = chat.asked
    assert system == DECOMPOSE_SYSTEM
    assert "never as instructions" in system
    assert json.loads(user.removeprefix("Spec: "))["walking_skeleton"] == "greet() end to end"


@pytest.mark.asyncio
async def test_the_grammar_enumerates_the_specs_own_criteria() -> None:
    """Constrained decoding makes a criterion that does not exist a token the model cannot
    emit, and makes an item without a command or a checked criterion unrepresentable."""
    producer, chat = _producer(VALID)
    await producer.decompose(_spec("AC-1", "AC-2"))
    ((_, _, schema),) = chat.asked

    assert schema == producer.schema(["AC-1", "AC-2"])
    item = schema["properties"]["items"]["items"]  # type: ignore[index]
    assert schema["properties"]["items"]["minItems"] == 1  # type: ignore[index]
    assert item["properties"]["acceptance_ids"]["items"]["enum"] == ["AC-1", "AC-2"]
    verification = item["properties"]["verification"]
    assert verification["properties"]["criteria_checked"]["items"]["enum"] == ["AC-1", "AC-2"]
    assert verification["properties"]["criteria_checked"]["minItems"] == 1
    assert verification["properties"]["commands"]["minItems"] == 1
    assert verification["required"] == ["commands", "criteria_checked"]
    assert item["properties"]["est_effort"]["enum"] == ["trivial", "low", "standard", "high", "max"]
    assert set(item["required"]) == set(item["properties"])


@pytest.mark.asyncio
async def test_a_spec_with_no_criteria_is_refused_before_the_model_is_asked() -> None:
    """An empty enum is a grammar nothing satisfies; asking would only waste a generation."""
    producer, chat = _producer(VALID)
    with pytest.raises(ValueError, match="no acceptance criteria cannot be decomposed"):
        await producer.decompose(_spec())
    assert chat.asked == []


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [{"items": []}, {"nope": 1}, {"items": "ws"}])
async def test_an_empty_or_missing_plan_is_refused(answer: dict[str, object]) -> None:
    producer, _ = _producer(answer)
    with pytest.raises(ValueError, match="non-empty items list"):
        await producer.decompose(_spec("AC-1"))


def _broken(mutate: object) -> dict[str, object]:
    answer = copy.deepcopy(VALID)
    mutate(answer["items"])  # type: ignore[operator]
    return answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        # validate_decomposition's rules: every criterion mapped, skeleton first and alone.
        (
            {"items": [_item("ws", acceptance=["AC-1"])]},
            "1 acceptance criterion/criteria unmapped: AC-2",
        ),
        (
            _broken(lambda items: items[0].update(depends_on=["cli-parsing"])),
            "walking skeleton item 'ws' must have no dependencies",
        ),
        # What only a fan-out would otherwise discover, after enqueueing part of the plan.
        (
            {
                "items": [
                    _item("ws", acceptance=["AC-1"]),
                    _item("b", acceptance=["AC-2"], depends_on=["c"]),
                    _item("c", acceptance=["AC-2"], depends_on=["ws"]),
                ]
            },
            "item 'b' depends on c, which does not come before it",
        ),
        (
            _broken(lambda items: items[1].update(depends_on=["cli-parsing"])),
            "item 'cli-parsing' depends on cli-parsing, which does not come before it",
        ),
        # What build.verify would otherwise discover, by running nothing.
        (
            {
                "items": [
                    _item("ws", acceptance=["AC-1"]),
                    _item("b", acceptance=["AC-2"], depends_on=["ws"], commands=["  "]),
                ]
            },
            "item 'b' has no verification command, so its verify gate would run nothing",
        ),
        (
            {
                "items": [
                    _item("ws", acceptance=["AC-1"]),
                    _item("b", acceptance=["AC-2"], depends_on=["ws"], checked=[]),
                ]
            },
            "item 'b' checks no acceptance criterion",
        ),
        # A gateway that is not really Ollama can ignore the enum; the check does not.
        (
            {
                "items": [
                    _item("ws", acceptance=["AC-1", "AC-9"]),
                    _item("b", acceptance=["AC-2"], depends_on=["ws"]),
                ]
            },
            "item 'ws' names criteria the spec does not define: AC-9",
        ),
        (
            {"items": [_item("ws", acceptance=["AC-1"]), _item("WS", acceptance=["AC-2"])]},
            "duplicate item_id(s): ws",
        ),
    ],
)
async def test_an_invalid_plan_is_refused_whole(answer: dict[str, object], expected: str) -> None:
    """Never a partial plan: one violation and nothing is returned at all."""
    producer, _ = _producer(answer)
    with pytest.raises(ValueError, match="model produced an invalid decomposition") as caught:
        await producer.decompose(_spec("AC-1", "AC-2"))
    assert expected in str(caught.value)


@pytest.mark.asyncio
async def test_an_unknown_dependency_is_named_once() -> None:
    """validate_decomposition already names a dependency on an item that does not exist;
    the ordering check stays quiet about it rather than reporting it twice."""
    answer = {
        "items": [
            _item("ws", acceptance=["AC-1"]),
            _item("b", acceptance=["AC-2"], depends_on=["ghost"]),
        ]
    }
    producer, _ = _producer(answer)
    with pytest.raises(ValueError) as caught:
        await producer.decompose(_spec("AC-1", "AC-2"))
    message = str(caught.value)
    assert "item 'b' depends on unknown item 'ghost'" in message
    assert "does not come before it" not in message


def test_the_producer_meets_its_declared_seams() -> None:
    producer = QwenloopWorkPlanProducer()
    assert isinstance(producer, QwenloopWorkPlanProducerInterface)
    assert isinstance(producer._chat, OllamaChatClientInterface)
    assert isinstance(producer._decoder, WorkPlanDecoderInterface)
    assert isinstance(producer._decoder, WorkPlanDecoder)
