# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for asking a local model a question whose answer must fit a schema.

Mirrors `vibey/infrastructure/engines/validated_ask.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from collections.abc import Callable, Mapping
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class JsonShapeCheckerInterface(Protocol):
    """Names every way a decoded JSON value breaks a JSON Schema."""

    def violations(self, value: object, schema: Mapping[str, object]) -> tuple[str, ...]:
        """Each violation as a sentence naming its path; empty when the value fits."""
        ...


@runtime_checkable
class ValidatedAskInterface(Protocol):
    """One question in JSON mode, its answer checked, and one re-ask naming what failed."""

    async def ask(
        self,
        system: str,
        user: str,
        schema: Mapping[str, object],
        *,
        subject: str,
        decode: Callable[[dict[str, object]], T],
    ) -> T:
        """`decode`'s result for an answer that fits `schema`, or `ModelAnswerRejected`
        (vibey.domain.errors) once the re-ask has failed too."""
        ...
