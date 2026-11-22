# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's port onto the user's own service manager (ADR-0101).

Implemented by `infrastructure/acp/service_loader.py`. Every command behind it is `launchctl` in
the user's `gui/<uid>` domain or `systemctl --user`: never the system domain, never sudo. Nothing
here raises for a refusal: an outcome says it. Blocking: the caller runs it off the loop.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vibey.application.acp.dto import UnitOutcome


@runtime_checkable
class ServiceLoaderInterface(Protocol):
    def available(self) -> bool:
        """Whether this user has a service manager to load units into now: launchd's
        `gui/<uid>` domain exists, or `systemctl --user` reaches a user manager."""
        ...

    def state(self, label: str) -> str:
        """`running`, `stopped...`, `not loaded`, or `unknown: ...`; never a guess."""
        ...

    def load(self, label: str, unit: str) -> UnitOutcome:
        """Load the unit at `unit` (the service manager's own file for `label`) and start it:
        `loaded`, `already-loaded` (nothing issued that would unload or replace it), or
        `failed` with the service manager's answer."""
        ...

    def restart(self, label: str) -> UnitOutcome:
        """Stop and start the loaded `label`: `restarted`, or `failed` with the answer."""
        ...

    def unload_commands(self, labels: Sequence[str]) -> tuple[str, ...]:
        """The commands the operator runs to stop and unload `labels`."""
        ...

    def domain(self) -> str:
        """Which service manager and domain units are loaded into, said to the operator."""
        ...
