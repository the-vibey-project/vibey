# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for what the automation-bootstrap admin merge verifies (vibey ADR-0016)."""

from __future__ import annotations

from typing import Protocol

from vibey_gh.config import GhConfig


class AutomationBootstrapGateInterface(Protocol):
    """Derives, from configuration, the two things `automation-bootstrap.yml` checks.

    That workflow is the one path that merges past PR automation, so the independent
    gates it waits on and the paths it lets a repair touch are the whole of its safety
    claim. Both are rendered into the deployed workflow; neither is a literal in it.
    """

    def required_checks(self, cfg: GhConfig) -> tuple[str, ...]:
        """Check-run names that must be present and green on the exact head, in order."""
        ...

    def excluded_checks(self) -> tuple[str, ...]:
        """Check-run names the bootstrap never waits on and never requires."""
        ...

    def scope_pattern(self, cfg: GhConfig) -> str:
        """The POSIX ERE every changed repository-root path must match."""
        ...

    def render(self, text: str, cfg: GhConfig) -> str:
        """`text` with every bootstrap placeholder replaced by its YAML-safe value."""
        ...
