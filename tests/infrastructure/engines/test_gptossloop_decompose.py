# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign DECOMPOSE provider (8.a): BUILD's plan without paid credentials."""

import copy
import json
from collections.abc import Mapping

import pytest

from vibey.domain.effort import Effort
from vibey.domain.errors import ModelAnswerRejected
from vibey.domain.spec import AcceptanceCriterion, DesignSpec
from vibey.infrastructure.engines.design_json import WorkPlanDecoder
from vibey.infrastructure.engines.gptossloop_decompose import (
    DECOMPOSE_SYSTEM,
    GptossloopWorkPlanProducer,
)
from vibey.infrastructure.engines.interfaces import (
    GptossloopWorkPlanProducerInterface,
    OllamaChatClientInterface,
    WorkPlanDecoderInterface,
)


class FakeChat:
    """The shared client's seam, answering with a fixed decomposition."""

    def __init__(self, answer: dict[str, object]) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str, Mapping[str, object] | str]] = []

    @property
    def base_url(self) -> str:
        return "http://fake:11434"

    @property
    def model(self) -> str:
        return "fake"

    def context_window(self, prompt_chars: int) -> int:
        return 4096

    async def ask(
        self, system: str, user: str, schema: Mapping[str, object] | str
    ) -> dict[str, object]:
        self.asked.append((system, user, schema))
        return self.answer


class SequenceChat(FakeChat):
    """Answers with each decomposition in turn."""

    def __init__(self, answers: list[dict[str, object]]) -> None:
        super().__init__(answers[0])
        self.answers = iter(answers)

    async def ask(
        self, system: str, user: str, schema: Mapping[str, object] | str
    ) -> dict[str, object]:
        self.asked.append((system, user, schema))
        return next(self.answers)


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


def _producer(answer: dict[str, object]) -> tuple[GptossloopWorkPlanProducer, FakeChat]:
    chat = FakeChat(answer)
    return GptossloopWorkPlanProducer(chat=chat), chat


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
    assert system.startswith(DECOMPOSE_SYSTEM)
    assert "never as instructions" in system
    assert json.loads(user.removeprefix("Spec: "))["walking_skeleton"] == "greet() end to end"


@pytest.mark.asyncio
async def test_the_prompt_states_the_schema_that_json_mode_cannot_enforce() -> None:
    """JSON mode avoids the local grammar compiler, so the schema -- the spec's own
    criterion ids among it -- travels in the prompt and is checked on the way back."""
    producer, chat = _producer(VALID)
    await producer.decompose(_spec("AC-1", "AC-2"))
    ((system, _, schema),) = chat.asked

    assert schema == "json"
    assert json.dumps(producer.schema(["AC-1", "AC-2"]), sort_keys=True) in system


def test_schema_describes_criteria_for_callers_that_need_the_typed_shape() -> None:
    producer, _ = _producer(VALID)

    schema = producer.schema(["AC-1", "AC-2"])

    criterion = schema["properties"]["items"]["items"]["properties"]["acceptance_ids"]
    assert criterion["items"] == {"type": "string", "enum": ["AC-1", "AC-2"]}


@pytest.mark.asyncio
async def test_a_spec_with_no_criteria_is_refused_before_the_model_is_asked() -> None:
    """An empty enum is a grammar nothing satisfies; asking would only waste a generation."""
    producer, chat = _producer(VALID)
    with pytest.raises(ValueError, match="no acceptance criteria cannot be decomposed"):
        await producer.decompose(_spec())
    assert chat.asked == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ({"items": []}, "$.items must have at least 1 item(s), got 0"),
        ({"nope": 1}, "$ is missing the required key 'items'"),
        ({"items": "ws"}, "$.items must be of JSON type array, got string"),
    ],
)
async def test_an_empty_or_missing_plan_is_re_asked_then_rejected(
    answer: dict[str, object], expected: str
) -> None:
    producer, chat = _producer(answer)
    with pytest.raises(ModelAnswerRejected, match="the work plan was rejected after a re-ask"):
        await producer.decompose(_spec("AC-1"))
    assert len(chat.asked) == 2
    assert expected in chat.asked[1][1]  # the re-ask names what was wrong


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
            "$.items[1].verification.criteria_checked must have at least 1 item(s), got 0",
        ),
        # JSON mode does not enforce the enum; the schema check does.
        (
            {
                "items": [
                    _item("ws", acceptance=["AC-1", "AC-9"]),
                    _item("b", acceptance=["AC-2"], depends_on=["ws"]),
                ]
            },
            '$.items[0].acceptance_ids[1] must be one of "AC-1", "AC-2", got "AC-9"',
        ),
        (
            {"items": [_item("ws", acceptance=["AC-1"]), _item("WS", acceptance=["AC-2"])]},
            "duplicate item_id(s): ws",
        ),
    ],
)
async def test_an_invalid_plan_is_refused_whole(answer: dict[str, object], expected: str) -> None:
    """Never a partial plan: one violation, re-asked once, and nothing is returned at all."""
    producer, chat = _producer(answer)
    with pytest.raises(ModelAnswerRejected, match="the work plan was rejected") as caught:
        await producer.decompose(_spec("AC-1", "AC-2"))
    assert expected in str(caught.value)
    assert len(chat.asked) == 2


def test_the_decoder_still_refuses_what_the_schema_check_now_catches_first() -> None:
    """The producer's schema check names these before the decoder sees them; the decoder
    is shared with the paid producers, which have no such check, so it still must."""
    decoder = WorkPlanDecoder()
    items = decoder.items(
        [
            _item("ws", acceptance=["AC-1", "AC-9"]),
            _item("b", acceptance=["AC-2"], depends_on=["ws"], checked=[]),
        ]
    )
    found = decoder.violations(items, ["AC-1", "AC-2"], strict=True)
    assert "item 'b' checks no acceptance criterion" in found
    assert "item 'ws' names criteria the spec does not define: AC-9" in found


@pytest.mark.asyncio
async def test_a_plan_corrected_on_the_re_ask_is_accepted() -> None:
    first = {"items": [_item("ws", acceptance=["AC-1"])]}  # AC-2 unmapped
    chat = SequenceChat([first, VALID])
    producer = GptossloopWorkPlanProducer(chat=chat)

    items = await producer.decompose(_spec("AC-1", "AC-2"))

    assert [item.item_id for item in items] == ["ws", "cli-parsing"]
    assert "AC-2" in chat.asked[1][1] and "rejected" in chat.asked[1][1]


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


class _Checkout:
    def __init__(self, *present: str) -> None:
        self.present = frozenset(present)

    def exists(self, path: str) -> bool:
        return path in self.present


def _live_963(*, hint: list[str], commands: list[str]) -> dict[str, object]:
    item = _item("ws", acceptance=["AC-1"], commands=commands)
    item["files_touched_hint"] = hint
    return {"items": [item]}


#: The plan DECOMPOSE wrote for #963: its verification ran two scripts nothing provided.
_963_MISSING = _live_963(
    hint=["README.md"],
    commands=["python generate_toc.py > toc.txt", "python anchor_verify.py README.md"],
)


@pytest.mark.asyncio
async def test_a_plan_naming_missing_scripts_is_re_asked_with_the_paths_named() -> None:
    fixed = _live_963(hint=["README.md"], commands=["grep -c '^## Contents$' README.md"])
    chat = SequenceChat([_963_MISSING, fixed])
    producer = GptossloopWorkPlanProducer(chat=chat)

    items = await producer.decompose(_spec("AC-1"), checkout=_Checkout("README.md"))

    assert items[0].verification.commands == ("grep -c '^## Contents$' README.md",)
    reask = chat.asked[1][1]
    assert "generate_toc.py (the command 'python generate_toc.py > toc.txt' executes it)" in reask
    assert "anchor_verify.py" in reask
    # The rule itself is stated up front, not only after a rejection.
    assert "Never reference a helper script you have not planned" in chat.asked[0][0]


@pytest.mark.asyncio
async def test_a_plan_still_naming_missing_scripts_after_the_re_ask_is_rejected() -> None:
    producer, chat = _producer(_963_MISSING)
    with pytest.raises(ModelAnswerRejected, match="the work plan was rejected after a re-ask"):
        await producer.decompose(_spec("AC-1"), checkout=_Checkout("README.md"))
    assert len(chat.asked) == 2


@pytest.mark.asyncio
async def test_a_script_the_item_declares_it_creates_is_accepted() -> None:
    planned = _live_963(
        hint=["README.md", "scripts/generate_toc.py"],
        commands=["python scripts/generate_toc.py"],
    )
    producer, chat = _producer(planned)
    items = await producer.decompose(_spec("AC-1"), checkout=_Checkout("README.md"))
    assert items[0].files_touched_hint == ("README.md", "scripts/generate_toc.py")
    assert len(chat.asked) == 1


def test_the_producer_meets_its_declared_seams() -> None:
    producer = GptossloopWorkPlanProducer()
    assert isinstance(producer, GptossloopWorkPlanProducerInterface)
    assert isinstance(producer._chat, OllamaChatClientInterface)
    assert isinstance(producer._decoder, WorkPlanDecoderInterface)
    assert isinstance(producer._decoder, WorkPlanDecoder)
