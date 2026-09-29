# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A question to the local model whose answer must fit a JSON Schema -- checked here.

The sovereign producers ask in JSON mode, not with the schema compiled to a grammar:
the grammars compiled from their larger schemas stalled GPT-OSS on the reference host
(81e19457c, ba74746e2). JSON mode guarantees well-formed JSON and nothing about its
shape, and that is how `design.interview` failed eleven times running with
`KeyError: 'question_id'`: the prompt no longer carried the schema at all, so the model
chose its own key names, and the provider indexed the answer instead of checking it.

So the schema goes back into the prompt as text, the decoded answer is checked against
it, and a violation is re-asked ONCE with the violations named. A second failure is
`ModelAnswerRejected` -- an ENGINE-class failure saying what was wrong -- never a bare
`KeyError`. Bounded: one question costs at most two model calls here (and the chat
client's own length retry beneath each).
"""

import json
from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

from vibey.domain.errors import ModelAnswerRejected
from vibey.infrastructure.engines.interfaces.ollama_chat_interface import (
    OllamaChatClientInterface,
)
from vibey.infrastructure.engines.interfaces.validated_ask_interface import (
    JsonShapeCheckerInterface,
)

T = TypeVar("T")

SCHEMA_INSTRUCTION = (
    "Answer with exactly one JSON object that satisfies this JSON Schema, using its key "
    "names exactly and nothing else:\n"
)

REASK_INSTRUCTION = (
    "Your previous answer was rejected because it does not satisfy the JSON Schema:\n"
    "{violations}\n"
    "Answer again with one JSON object that satisfies the schema exactly."
)


class JsonShapeChecker:
    """The JSON Schema subset the sovereign producers' schemas use, checked exhaustively.

    `type`, `properties`, `required`, `items`, `minItems`, `maxItems` and `enum` -- the
    keywords `QUESTIONS_SCHEMA`, `SPEC_SCHEMA`, `RESEARCH_SCHEMA` and the decompose schema
    are written in. A keyword outside the subset is ignored, never guessed at.

    Written here rather than imported (ADR-0017): nothing in the family validates JSON
    Schema, no JSON Schema library is a dependency, and pydantic validates Python types,
    not the schema documents these producers already keep.
    """

    #: A re-ask prompt that lists a hundred violations is a prompt too long to help.
    MAX_VIOLATIONS = 12

    _TYPES: dict[str, tuple[type, ...]] = {
        "object": (dict,),
        "array": (list,),
        "string": (str,),
        "boolean": (bool,),
        "integer": (int,),
        "number": (int, float),
    }

    def violations(self, value: object, schema: Mapping[str, object]) -> tuple[str, ...]:
        found: list[str] = []
        self._check(value, schema, "$", found)
        return tuple(found[: self.MAX_VIOLATIONS])

    def _check(
        self, value: object, schema: Mapping[str, object], path: str, found: list[str]
    ) -> None:
        expected = schema.get("type")
        if isinstance(expected, str) and not self._is(value, expected):
            found.append(f"{path} must be of JSON type {expected}, got {self._json_type(value)}")
            return
        enum = schema.get("enum")
        if isinstance(enum, list) and value not in enum:
            allowed = ", ".join(json.dumps(item) for item in enum)
            found.append(f"{path} must be one of {allowed}, got {json.dumps(value)}")
        if isinstance(value, dict):
            self._check_object(value, schema, path, found)
        if isinstance(value, list):
            self._check_array(value, schema, path, found)

    def _check_object(
        self,
        value: Mapping[str, object],
        schema: Mapping[str, object],
        path: str,
        found: list[str],
    ) -> None:
        required = schema.get("required")
        for key in required if isinstance(required, list) else []:
            if key not in value:
                found.append(f"{path} is missing the required key {key!r}")
        properties = schema.get("properties")
        for key, child in (properties if isinstance(properties, Mapping) else {}).items():
            if key in value and isinstance(child, Mapping):
                self._check(value[key], child, f"{path}.{key}", found)

    def _check_array(
        self, value: Sequence[object], schema: Mapping[str, object], path: str, found: list[str]
    ) -> None:
        low = schema.get("minItems")
        if isinstance(low, int) and len(value) < low:
            found.append(f"{path} must have at least {low} item(s), got {len(value)}")
        high = schema.get("maxItems")
        if isinstance(high, int) and len(value) > high:
            found.append(f"{path} must have at most {high} item(s), got {len(value)}")
        items = schema.get("items")
        if isinstance(items, Mapping):
            for index, item in enumerate(value):
                self._check(item, items, f"{path}[{index}]", found)

    def _is(self, value: object, expected: str) -> bool:
        """Whether `value` is of JSON type `expected`; a type outside the subset passes."""
        if expected not in self._TYPES:
            return True
        # bool is an int in Python and never a number in JSON.
        if isinstance(value, bool) and expected in ("integer", "number"):
            return False
        return isinstance(value, self._TYPES[expected])

    @staticmethod
    def _json_type(value: object) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "array"
        if isinstance(value, str):
            return "string"
        return "number"


class ValidatedAsk:
    """One question in JSON mode, its answer checked, and one re-ask naming what failed."""

    def __init__(
        self,
        chat: OllamaChatClientInterface,
        *,
        checker: JsonShapeCheckerInterface | None = None,
        reasks: int = 1,
    ) -> None:
        if reasks < 0:
            raise ValueError(f"reasks must not be negative, got {reasks}")
        self._chat = chat
        self._checker = checker if checker is not None else JsonShapeChecker()
        self._reasks = reasks

    async def ask(
        self,
        system: str,
        user: str,
        schema: Mapping[str, object],
        *,
        subject: str,
        decode: Callable[[dict[str, object]], T],
    ) -> T:
        instructed = f"{system}\n\n{SCHEMA_INSTRUCTION}{json.dumps(schema, sort_keys=True)}"
        prompt = user
        violations: tuple[str, ...] = ()
        for _ in range(1 + self._reasks):
            answer = await self._chat.ask(instructed, prompt, "json")
            violations = self._checker.violations(answer, schema)
            if not violations:
                try:
                    return decode(answer)
                except (KeyError, TypeError, ValueError) as exc:
                    # What the schema cannot say -- a non-empty default, a criterion that
                    # exists, dependencies in order -- the caller's decoder does.
                    violations = (self._described(exc),)
            prompt = f"{user}\n\n" + REASK_INSTRUCTION.format(
                violations="\n".join(f"- {violation}" for violation in violations)
            )
        raise ModelAnswerRejected(subject, violations)

    @staticmethod
    def _described(exc: Exception) -> str:
        if isinstance(exc, KeyError):
            return f"missing the key {exc.args[0]!r}"
        return str(exc)
