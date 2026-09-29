# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Asking the local model in JSON mode, checking the answer, and re-asking once."""

import json
from collections.abc import Mapping

import pytest

from vibey.domain.errors import ModelAnswerRejected
from vibey.domain.job import FailureClass
from vibey.infrastructure.engines.interfaces import (
    JsonShapeCheckerInterface,
    ValidatedAskInterface,
)
from vibey.infrastructure.engines.validated_ask import (
    REASK_INSTRUCTION,
    SCHEMA_INSTRUCTION,
    JsonShapeChecker,
    ValidatedAsk,
)

SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "blocking": {"type": "boolean"},
                    "kind": {"type": "string", "enum": ["hard", "soft"]},
                },
                "required": ["question_id", "blocking"],
            },
        }
    },
    "required": ["questions"],
}


class ScriptedChat:
    """The chat client's seam, answering each question with the next scripted answer."""

    def __init__(self, *answers: dict[str, object]) -> None:
        self.answers = iter(answers)
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
        return next(self.answers)


GOOD = {"questions": [{"question_id": "q1", "blocking": True}]}
BAD = {"questions": [{"id": "q1", "blocking": "yes"}]}


def test_both_classes_meet_their_declared_seams() -> None:
    assert isinstance(JsonShapeChecker(), JsonShapeCheckerInterface)
    assert isinstance(ValidatedAsk(ScriptedChat()), ValidatedAskInterface)


def test_a_value_that_fits_has_no_violations() -> None:
    assert JsonShapeChecker().violations(GOOD, SCHEMA) == ()


def test_every_violation_is_named_with_its_path() -> None:
    found = JsonShapeChecker().violations(
        {"questions": [{"id": "q1", "blocking": "yes", "kind": "sideways"}] * 3}, SCHEMA
    )
    assert found[0] == "$.questions must have at most 2 item(s), got 3"
    assert "$.questions[0] is missing the required key 'question_id'" in found
    assert "$.questions[0].blocking must be of JSON type boolean, got string" in found
    assert '$.questions[2].kind must be one of "hard", "soft", got "sideways"' in found


def test_a_missing_or_short_array_and_a_wrong_top_level_type_are_named() -> None:
    checker = JsonShapeChecker()
    assert checker.violations({}, SCHEMA) == ("$ is missing the required key 'questions'",)
    assert checker.violations({"questions": []}, SCHEMA) == (
        "$.questions must have at least 1 item(s), got 0",
    )
    assert checker.violations([1], SCHEMA) == ("$ must be of JSON type object, got array",)


@pytest.mark.parametrize(
    ("value", "expected", "fits"),
    [
        (1, "integer", True),
        (True, "integer", False),
        (1.5, "number", True),
        (False, "number", False),
        ("x", "string", True),
        (None, "string", False),
        ({}, "object", True),
        ([], "array", True),
        (True, "boolean", True),
        ("anything", "null", True),  # outside the subset: passes, never guessed at
    ],
)
def test_json_types_follow_json_not_python(value: object, expected: str, fits: bool) -> None:
    assert (JsonShapeChecker().violations(value, {"type": expected}) == ()) is fits


@pytest.mark.parametrize(
    ("value", "name"),
    [
        (None, "null"),
        (True, "boolean"),
        ({}, "object"),
        ([], "array"),
        ("s", "string"),
        (2, "number"),
    ],
)
def test_the_actual_type_is_named_in_json_terms(value: object, name: str) -> None:
    other = "string" if name != "string" else "integer"
    (found,) = JsonShapeChecker().violations(value, {"type": other})
    assert found.endswith(f"got {name}")


def test_malformed_schema_keywords_are_ignored_rather_than_guessed_at() -> None:
    schema: dict[str, object] = {
        "enum": "not a list",
        "required": "not a list",
        "properties": {"a": "not a schema"},
        "items": "not a schema",
        "minItems": "1",
    }
    checker = JsonShapeChecker()
    assert checker.violations({"a": 1}, schema) == ()
    assert checker.violations([1], schema) == ()
    assert checker.violations({"a": 1}, {"properties": "not a mapping"}) == ()


def test_a_flood_of_violations_is_capped() -> None:
    schema: dict[str, object] = {"type": "array", "items": {"type": "string"}}
    found = JsonShapeChecker().violations(list(range(50)), schema)
    assert len(found) == JsonShapeChecker.MAX_VIOLATIONS


@pytest.mark.asyncio
async def test_a_good_first_answer_is_decoded_and_the_schema_is_stated() -> None:
    chat = ScriptedChat(GOOD)
    result = await ValidatedAsk(chat).ask(
        "be terse", "the ledger", SCHEMA, subject="a batch", decode=lambda data: data["questions"]
    )
    assert result == GOOD["questions"]
    ((system, user, mode),) = chat.asked
    assert mode == "json"  # JSON mode: the grammar is not compiled
    assert system == f"be terse\n\n{SCHEMA_INSTRUCTION}{json.dumps(SCHEMA, sort_keys=True)}"
    assert user == "the ledger"


@pytest.mark.asyncio
async def test_a_bad_answer_is_re_asked_once_naming_the_violations() -> None:
    chat = ScriptedChat(BAD, GOOD)
    result = await ValidatedAsk(chat).ask("s", "u", SCHEMA, subject="a batch", decode=dict)
    assert result == GOOD
    reask = chat.asked[1][1]
    assert reask.startswith("u\n\n")
    assert "- $.questions[0] is missing the required key 'question_id'" in reask
    assert REASK_INSTRUCTION.splitlines()[-1] in reask


@pytest.mark.asyncio
async def test_a_second_bad_answer_is_a_typed_engine_failure() -> None:
    chat = ScriptedChat(BAD, BAD)
    with pytest.raises(ModelAnswerRejected) as caught:
        await ValidatedAsk(chat).ask("s", "u", SCHEMA, subject="a batch", decode=dict)
    assert caught.value.failure_class is FailureClass.ENGINE
    assert caught.value.subject == "a batch"
    assert "$.questions[0].blocking must be of JSON type boolean" in caught.value.violations[1]
    assert isinstance(caught.value, ValueError)
    assert len(chat.asked) == 2


@pytest.mark.asyncio
async def test_a_decoder_refusal_is_re_asked_in_the_decoders_words() -> None:
    def decode(data: dict[str, object]) -> object:
        if data.get("round") == 1:
            raise KeyError("question_id")
        raise ValueError("every design question requires a proposed default")

    chat = ScriptedChat({"round": 1}, {"round": 2})
    with pytest.raises(ModelAnswerRejected) as caught:
        await ValidatedAsk(chat).ask("s", "u", {"type": "object"}, subject="x", decode=decode)
    assert "- missing the key 'question_id'" in chat.asked[1][1]
    assert caught.value.violations == ("every design question requires a proposed default",)


@pytest.mark.asyncio
async def test_re_asks_are_configurable_and_never_negative() -> None:
    chat = ScriptedChat(BAD)
    with pytest.raises(ModelAnswerRejected):
        await ValidatedAsk(chat, reasks=0).ask("s", "u", SCHEMA, subject="x", decode=dict)
    assert len(chat.asked) == 1
    with pytest.raises(ValueError, match="reasks must not be negative"):
        ValidatedAsk(chat, reasks=-1)
