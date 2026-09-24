"""What `storm_turn_pool.py` promises, declared beside it (ADR-0016, sub-doctrine 9.b).

The turn pool is the corpus source `vibey-gh slots corpus` samples from: storm turns built
as the chat payloads qwenloop sends -- from a storm's own run records when it has them, and
from the storm's committed lane specs when it does not. Declares; never consumes.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TurnPoolBuilderInterface(Protocol):
    """Rebuilds qwenloop runs as `vibey-gh/turn-pool/1` lines."""

    @staticmethod
    def repair_text(qwenlane: Path) -> str:
        """The repair text a lane's later attempts append (`qwenlane.REPAIR`), read verbatim."""
        ...

    def runs(self, lanes: Path) -> list[Path]:
        """Every qwenloop run directory under the storm's `lanes/`, oldest first per lane."""
        ...

    def build(self, run_dirs: Iterable[Path]) -> Iterator[dict[str, Any]]:
        """One pool line per run: its preamble, and per turn what the loop appended."""
        ...


@runtime_checkable
class SpecTurnPoolInterface(Protocol):
    """Builds storm-shaped runs from the storm's committed specs and the repository's files."""

    def build(self, specs: list[Path]) -> Iterator[dict[str, Any]]:
        """One pool line per spec: qwenloop's own preamble for it, then `read_file` turns."""
        ...
