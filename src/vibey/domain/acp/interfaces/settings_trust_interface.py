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
        """The user's settings, narrowed by each key in `project_keys` in its only stricter
        direction: a switch turned off, PostgreSQL refused, services or modes dropped, a rate
        slower, a timeout or cap lower. Nothing the project says widens, raises or loosens a
        value; a key with no stricter direction, or one not classified, is the user's alone."""
        ...
