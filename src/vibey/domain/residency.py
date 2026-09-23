# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure residency policy implementation for seat slugs and model selection.

This module implements the logic described in ADR‑0046.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

# Constants as per ADR‑0046
RESERVED_SEATS: Final[frozenset[str]] = frozenset({"probe", "dead"})
UNROUTABLE_NO_MODEL: Final = "no local model can carry this job"
CHOSEN_RESIDENT: Final = "resident"
CHOSEN_DEFAULT: Final = "default"
CHOSEN_FIRST_DECLARED: Final = "first declared"
_OUTSIDE_SLUG: Final = re.compile(r"[^a-z0-9-]")


class SeatSlug:
    """Utilities for normalising and validating seat names.

    No state – all methods are pure.
    """

    def of(self, name: str) -> str:
        slug = _OUTSIDE_SLUG.sub("-", name.lower())
        if not slug:
            raise ValueError(f"seat name {name!r} is empty")
        if slug in RESERVED_SEATS:
            raise ValueError(f"seat name {name!r} slugs to {slug!r}, which is reserved")
        return slug

    def of_paid(self, engine_id: str, model: str | None = None) -> str:
        return engine_id if model is None else f"{engine_id}.{self.of(model)}"

    def unique(self, names: Sequence[str]) -> Mapping[str, str]:
        seats: dict[str, str] = {}
        for name in names:
            slug = self.of(name)
            if slug in seats:
                raise ValueError(f"seats {slug} and {slug} share the slug {slug}")
            seats[slug] = name
        return MappingProxyType(seats)


@dataclass(frozen=True, slots=True)
class ModelDeclaration:
    name: str
    context_window: int

    def __post_init__(self) -> None:
        if self.context_window < 1:
            raise ValueError(
                f"ModelDeclaration.context_window must be at least 1, got {self.context_window}"
            )


@dataclass(frozen=True, slots=True)
class ModelChoice:
    model: str
    switched: bool
    reason: str


class ResidencyPolicy:
    """Choose a model based on residency and declared model windows."""

    def choose(
        self,
        *,
        resident: str | None,
        default: str | None,
        declared: Sequence[ModelDeclaration],
        model_pin: str | None,
        min_context: int | None,
    ) -> ModelChoice | None:
        order: list[tuple[str | None, str]] = [
            (resident, CHOSEN_RESIDENT),
            (default, CHOSEN_DEFAULT),
            *((d.name, CHOSEN_FIRST_DECLARED) for d in declared),
        ]
        for name, reason in order:
            if name is not None and self._can_carry(name, declared, model_pin, min_context):
                switched = resident is not None and name != resident
                return ModelChoice(model=name, switched=switched, reason=reason)
        return None

    @staticmethod
    def _can_carry(
        name: str,
        declared: Sequence[ModelDeclaration],
        model_pin: str | None,
        min_context: int | None,
    ) -> bool:
        declaration = next((d for d in declared if d.name == name), None)
        if declaration is None:
            return False
        if model_pin is not None and name != model_pin:
            return False
        return min_context is None or declaration.context_window >= min_context
