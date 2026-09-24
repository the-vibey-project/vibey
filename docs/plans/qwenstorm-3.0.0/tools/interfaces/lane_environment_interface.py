"""What a lane's environment promises, declared beside `lane_environment.py` (sub-doctrine 9.b).

Declares; never consumes. `tests/meta/test_storm_lane_environment.py` holds the
implementation to it, so the declaration cannot drift from the class it describes.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class LaneEnvironmentInterface(Protocol):
    """The environment every command of one storm lane runs in."""

    lane: Path

    def inside(self, path: str | Path) -> bool:
        """True when `path` lies within the lane's workspace."""
        ...

    def build(self, inherited: Mapping[str, str]) -> dict[str, str]:
        """The lane's environment: its own venv first, nothing pointing outside the lane."""
        ...

    def verify(self, env: Mapping[str, str]) -> Path:
        """The lane's python under `env`; raises when it resolves outside the lane."""
        ...

    def enter(self, environ: MutableMapping[str, str] | None = None) -> Path:
        """Make `environ` (default: this process's) the lane's, after verifying it."""
        ...
