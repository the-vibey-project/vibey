# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/host_tuning.py` implements. Interfaces declare; they never consume.

A *backend* knows one kind of setting (a service's environment, a desktop application's
settings file, the database's configuration, a regenerable cache, a log): it observes the
host's actual value, applies the declared one and puts the prior one back. The *journal* is
the append-only record of every change and the value it replaced. The *tuner* walks the
declared items through their backends under each item's gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class TuningBackendInterface(Protocol):
    """One kind of host setting."""

    def observe(self, item: Any) -> Any:
        """The declared value against the host's actual one, as an Observation."""
        ...

    def apply(self, item: Any) -> list[str]:
        """Make the host match the item; journal the prior value; say what was done and
        what a person still has to do (a restart, a root-owned file)."""
        ...

    def undo(self, item: Any, entry: Mapping[str, Any]) -> list[str]:
        """Put back the prior value `entry` recorded when the item was applied."""
        ...


class TuningJournalInterface(Protocol):
    """The append-only record of every change the tuner made."""

    def append(self, entry: Mapping[str, Any]) -> None:
        """Add one entry; never rewrite an earlier one."""
        ...

    def entries(self) -> list[dict[str, Any]]:
        """Every entry, oldest first."""
        ...

    def last(self, key: str, actions: Sequence[str]) -> dict[str, Any] | None:
        """The newest entry for `key` whose action is one of `actions`."""
        ...


class HostTunerInterface(Protocol):
    """Declared tuning against the host: check, apply under each gate, undo."""

    def check(self, kinds: Sequence[str] | None = None) -> list[Any]:
        """One Observation per declared item (of `kinds`, when given)."""
        ...

    def apply(self, only: Sequence[str] = (), dry_run: bool = False) -> list[str]:
        """Apply every item whose gate is open (or only those named); report each one."""
        ...

    def undo(self, key: str) -> list[str]:
        """Restore what the journal says `key` replaced."""
        ...
