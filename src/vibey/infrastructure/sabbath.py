# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Sabbath on this host, for the engine (sub-doctrine 8.i; ADR-0070).

The window, the location sources and the resume machinery are vibey-gh's
(`vibey_gh.sabbath_guard`); this adapter feeds them the operator's LOCAL `vibey.toml`
`[sabbath]` table -- where an explicit latitude/longitude may live, since that file is
never committed -- and answers the application's one question through
`SabbathGateInterface`.
"""

import dataclasses
import tomllib
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vibey_gh.config import SabbathConfig
from vibey_gh.sabbath_guard import SabbathGuard

from vibey.domain.sabbath import RestWindowInterface
from vibey.infrastructure.interfaces.sabbath_interface import HostSabbathGateInterface

__all__ = ["HostSabbathGate"]


class HostSabbathGate(HostSabbathGateInterface):
    """Answers `SabbathGateInterface` from this machine's clock and location."""

    def __init__(self, guard: SabbathGuard) -> None:
        self._guard = guard

    @classmethod
    def from_table(
        cls,
        table: Mapping[str, Any],
        *,
        home: Path,
        environ: Mapping[str, str] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> "HostSabbathGate":
        """From a `[sabbath]` table. An unknown key is refused by name, not ignored."""
        known = {field.name for field in dataclasses.fields(SabbathConfig)}
        unknown = sorted(set(table) - known)
        if unknown:
            raise ValueError(f"[sabbath] has no key {unknown[0]!r}")
        guard = SabbathGuard(SabbathConfig(**dict(table)), home=home, environ=environ, clock=clock)
        return cls(guard)

    @classmethod
    def from_toml(
        cls, path: Path, *, home: Path, environ: Mapping[str, str] | None = None
    ) -> "HostSabbathGate":
        """From `path`'s `[sabbath]` table; a missing file or table keeps the defaults --
        the Sabbath is on unless a file says otherwise (8.i has no exception)."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        table = data.get("sabbath", {})
        if not isinstance(table, dict):
            raise ValueError("[sabbath] must be a table")
        return cls.from_table(table, home=home, environ=environ)

    def hold(self) -> RestWindowInterface | None:
        return self._guard.hold()

    def describe(self) -> list[str]:
        """The window, the zone and the location source, for `vibey doctor` (10.f)."""
        return self._guard.describe()

    def location_resolved(self) -> bool:
        return self._guard.location() is not None
