"""What the durability gate promises, declared beside `storm_durability.py` (sub-doctrine 9.b).

Declares; never consumes. `tests/meta/test_storm_durability.py` holds the implementation to
it, so the declaration cannot drift from the classes it describes.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PlatformStorageInterface(Protocol):
    """Where one operating system keeps files through a reboot, and where it throws them away.

    The one seam that knows the platform. macOS and Linux implement it; Windows (#1097) is
    the implementation still to write: %LOCALAPPDATA%\\vibey\\storm durable, %TEMP% volatile.
    """

    name: str

    def default_home(self, environ: Mapping[str, str]) -> Path:
        """Where storm work lives when nothing declares otherwise."""
        ...

    def fixed_volatile(self) -> tuple[tuple[str, str], ...]:
        """Every location this OS empties, with when and why."""
        ...

    def session_volatile(self) -> tuple[tuple[str, str], ...]:
        """The environment variables that name this session's temporary directories."""
        ...


@runtime_checkable
class VolatileLocationsInterface(Protocol):
    """Where the operating system discards files: at boot, by age, or when a session ends."""

    def roots(self) -> tuple[tuple[Path, str], ...]:
        """Every volatile location, resolved through symlinks, with why it is volatile."""
        ...

    def containing(self, path: Path) -> tuple[Path, str] | None:
        """The volatile location `path` resolves under, and why; None when it is durable."""
        ...


@runtime_checkable
class StormHomeInterface(Protocol):
    """The one declared durable directory all storm work on a machine lives under."""

    def resolve(self) -> tuple[Path, str]:
        """The home, and what declared it: the environment, storm.toml, or the default."""
        ...

    def worktree(self, name: str) -> Path:
        """Where the worktree called `name` lives: directly under the home."""
        ...

    def push_lock(self) -> Path:
        """The machine's shared push lock, one per home."""
        ...


@runtime_checkable
class DurabilityGateInterface(Protocol):
    """Refuses to let storm work be placed where the operating system will discard it."""

    def disposable(self) -> str | None:
        """The reason the storm root gives for being throwaway, or None."""
        ...

    def inspect(self, named: Mapping[str, Path]) -> list[Any]:
        """Every named path that resolves under a volatile location."""
        ...

    def refusal(self, hits: list[Any], key: str) -> str:
        """The refusal: what, where it really is, why that is lost, and the key that moves it."""
        ...

    def enforce(self, named: Mapping[str, Path], key: str) -> None:
        """Return when every named path is durable; otherwise print why and exit 78."""
        ...
