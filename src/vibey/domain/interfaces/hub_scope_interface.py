# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind deciding what a hub caller may do.

Mirrors `vibey/domain/hub_scope.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.hub_scope import HubAction, HubScope


@runtime_checkable
class HubScopePolicyInterface(Protocol):
    """Decides whether granted scopes permit an action, deny by default."""

    def permits(self, granted: frozenset[HubScope], action: HubAction) -> bool:
        """True only when `granted` holds the one scope `action` needs."""
        ...

    def action_for_gate(self, kind: str) -> HubAction:
        """The action answering a gate of `kind` counts as: spending, or a plain answer."""
        ...

    def reserved(self, capability: str) -> bool:
        """True when `capability` is one no scope grants and no route offers."""
        ...

    @staticmethod
    def command_words(argv: tuple[str, ...]) -> tuple[str, ...]:
        """A vibey command line's command words, after its leading global options."""
        ...

    def reserved_command(self, argv: tuple[str, ...]) -> str | None:
        """The reserved capability a vibey command line reaches, or None."""
        ...

    def scopes_for_command(self, argv: tuple[str, ...]) -> frozenset[HubScope]:
        """Every scope a caller must hold to send `argv` to the workflows."""
        ...

    def parse(self, values: frozenset[str]) -> frozenset[HubScope]:
        """The scopes `values` names; `ValueError` for any name this version lacks."""
        ...
