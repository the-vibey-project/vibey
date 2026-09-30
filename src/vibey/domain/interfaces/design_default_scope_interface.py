# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind a DESIGN question's narrowest-scope default.

Mirrors `vibey/domain/design_default_scope.py` (ADR-0016). Interfaces declare; they
never consume. The domain types the seam is declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.design_default_scope import (
        DefaultScope,
        ScopeClassification,
        ScopedDefault,
    )


@runtime_checkable
class DesignDefaultScopeGuardInterface(Protocol):
    """Decides the default a DESIGN question is recorded with."""

    def classify(self, question: str, *, intake: str) -> ScopeClassification:
        """The evidence: is it yes/no, does it extend, which artefacts beyond the intake,
        and does it ask about delivering the change the intake asks for."""
        ...

    def declines(self, default: str) -> bool:
        """True when the default already declines, so it is already the minimal one."""
        ...

    def scope(
        self, question: str, default: str, *, intake: str, policy: DefaultScope
    ) -> ScopedDefault:
        """The default to declare under `policy`, with the model's own when rewritten."""
        ...
