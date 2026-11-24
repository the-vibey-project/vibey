# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of `capabilities/instruction_files.py`: the repository's own instruction files as
text for the system prompt (SP-LOOPS Phase 4, Task 6; R8; moved from claudeloop in Phase 5,
R12)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class InstructionTextInterface(Protocol):
    @property
    def text(self) -> str:
        """The blocks and named lines, in the order the names were given; empty when no file
        exists."""
        ...

    @property
    def inlined(self) -> tuple[str, ...]:
        """The names whose whole text is in `text`."""
        ...

    @property
    def named(self) -> tuple[str, ...]:
        """The names that exist but are only named in `text`, each with the reason."""
        ...


@runtime_checkable
class InstructionFileReaderInterface(Protocol):
    def read(
        self,
        cwd: Path,
        names: Sequence[str],
        max_bytes: int,
        *,
        budget_chars: int | None = None,
    ) -> InstructionTextInterface:
        """Reads `cwd/<name>` for each name, in order, and never any other path. A regular UTF-8
        file of at most `max_bytes` bytes is inlined whole under `## Repository instructions
        (<name>)`. A larger file is named with its size and never truncated. A symlink, a file
        that is not regular, bytes that are not UTF-8 and a file that cannot be opened are each
        named with the reason. A missing file is skipped and counted nowhere.

        With `budget_chars`, a file whose block, with the blank line before it, would not fit
        what the text before it leaves of `budget_chars` is named instead, with its size, as
        not fitting this loop's standing context; it is never cut. A line that names a file
        counts against the budget too. `None` (claudeloop) applies no budget."""
        ...
