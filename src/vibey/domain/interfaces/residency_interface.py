# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interfaces for the residency domain.

Copied structure from other interface modules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.residency import (
        ModelChoice,
        ModelDeclaration,
    )


@runtime_checkable
class SeatSlugInterface(Protocol):
    def of(self, name: str) -> str: ...
    def of_paid(self, engine_id: str, model: str | None = None) -> str: ...
    def unique(self, names: Sequence[str]) -> Mapping[str, str]: ...


@runtime_checkable
class ModelDeclarationInterface(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def context_window(self) -> int: ...


@runtime_checkable
class ModelChoiceInterface(Protocol):
    @property
    def model(self) -> str: ...
    @property
    def switched(self) -> bool: ...
    @property
    def reason(self) -> str: ...


@runtime_checkable
class ResidencyPolicyInterface(Protocol):
    def choose(
        self,
        *,
        resident: str | None,
        default: str | None,
        declared: Sequence[ModelDeclaration],
        model_pin: str | None,
        min_context: int | None,
    ) -> ModelChoice | None: ...
