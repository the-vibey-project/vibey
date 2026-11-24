# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of a run's skill shelf: the skills and plugin commands a loop reads on demand
(SP-LOOPS Phase 5, R9-R11)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Self, runtime_checkable

from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.interfaces.plugin_command_index_interface import (
    PluginCommandIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.safe_text_interface import SafeTextInterface
from vibey_runners.common.capabilities.interfaces.skill_index_interface import (
    SkillIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.shelf_entry import ShelfEntry
from vibey_runners.common.capabilities.shelf_page import ShelfPage
from vibey_runners.common.capabilities.shelf_text import ShelfText


@runtime_checkable
class SkillShelfInterface(Protocol):
    @classmethod
    def of(
        cls,
        document: SnapshotDocumentInterface,
        *,
        skills: SkillIndexInterface | None = None,
        commands: PluginCommandIndexInterface | None = None,
        text: SafeTextInterface | None = None,
        reader: FileReaderInterface | None = None,
    ) -> Self:
        """The shelf of `document`: the skills it names, in its order (re-indexed from its own
        plugin copies, never one it does not name), then its plugins' commands in plugin order
        (one named like a skill is skipped). Nothing raises for what a plugin holds."""
        ...

    @property
    def entries(self) -> tuple[ShelfEntry, ...]: ...

    @property
    def skipped(self) -> tuple[tuple[Path, str], ...]:
        """(path, reason) for each skill or command that is not on the shelf, and why."""
        ...

    def page(self, number: int, answer_chars: int) -> ShelfPage:
        """Page `number` (from 1) of the entries, filled greedily in order, each page's JSON
        (`[{"name", "kind", "description"}, ...]`, ASCII-escaped, default separators) at most
        `answer_chars`; an entry too long for any page shows its name only. Raises
        `SkillShelfError` for a page out of range (naming the shelf's size and the page count)
        and `ValueError` for a budget below `MIN_ANSWER_CHARS`."""
        ...

    def read(self, name: str, number: int, answer_chars: int) -> ShelfText:
        """Page `number` (from 1) of the text of the skill or command `name`, read with the
        bounded reader, in pages of at most `answer_chars` characters broken at line ends where
        a line fits; the pages, joined, are the text exactly, never cut. Raises
        `SkillShelfError` for an unknown name, a page out of range or a text that cannot be
        read now, and `ValueError` for a budget below `MIN_ANSWER_CHARS`."""
        ...
