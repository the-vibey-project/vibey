# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/settings_trust.py` (ADR-0016, ADR-0101). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.settings import AcpSettings


@runtime_checkable
class AcpSettingsTrustInterface(Protocol):
    """Merges the user's `[acp]` (the powers) with a project's (restrictions only). Pure."""

    def merge(
        self, user: AcpSettings, project: AcpSettings, project_keys: frozenset[str]
    ) -> AcpSettings:
        """The user's settings, narrowed by every key in `project_keys` that only narrows:
        a grant the project turns off, a service it drops, PostgreSQL it says `never` to, a
        slower or shorter bound. A key the project could use to widen anything, or that reaches
        a service unit, a command line or a file outside the project, is the user's alone."""
        ...
