# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for deciding what `[install] pin_version` pins (vibey ADR-0016).

Resolved once per command and handed to every render, so a `vibey-gh install` that renders
sixteen workflows asks the interpreter's metadata one question, not sixteen, and every
workflow it writes agrees with every other one about the release.

`FallbackPin` is the answer's shape. It is data, declared here beside the seam that speaks
it, the standing `vibey.application.interfaces` gives its result records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from vibey_gh.config import GhConfig


@dataclass(frozen=True, slots=True)
class FallbackPin:
    """What the fallback `pip install <fallback_package>` is pinned to, and why not.

    `version` is the release to pin, or `None` to leave the install floating.
    `from_repository` is true only when that release is the repository's OWN `[project]
    version` — the one case a version bump changes the rendered workflows.
    `notice` explains a pin that was asked for and could not be honoured; it is `None`
    whenever nothing was asked for, or the pin holds.
    """

    version: str | None
    from_repository: bool = False
    notice: str | None = None


@runtime_checkable
class FallbackPinResolverInterface(Protocol):
    """Decides the fallback pin for one repository's configuration."""

    def resolve(self, cfg: GhConfig) -> FallbackPin:
        """The pin `cfg` asks for, or a floating install with the reason it floats."""
        ...
