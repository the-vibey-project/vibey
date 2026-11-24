# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run's skill shelf: the skills and plugin commands a loop may read on demand, from its
capability document (SP-LOOPS Phase 5, R9-R11; Review Focus 4).

**What is on it.** First the skills the document names (`document.skills`, `plugin:skill`), in
that order, re-indexed from the run's own plugin copies; a skill the document does not name is
never shelved (Phase 4, R6), and one it names that its plugin copy no longer holds is a skipped
row. Then the plugin commands (`commands/*.md`, R10), in plugin order; a command whose qualified
name is already a skill's is a skipped row. Descriptions are one safe line (`SafeText`).

**Paging the list.** `page` fills pages greedily, in order, so each page's JSON -- the entries as
`[{"name", "kind", "description"}, ...]`, measured in the widest form a tool could write it
(`json.dumps` defaults: ASCII escapes and `", "` separators) -- is at most `answer_chars`. An
entry too long for any page alone is shown with its name only (an empty description); a name is
at most 257 characters, so it always fits the `MIN_ANSWER_CHARS` floor.

**Reading a text.** `read` reads the file whole with the bounded reader, at most
`SKILL_MAX_BYTES`, and splits it into pages of at most `answer_chars` characters: lines go onto
a page while they fit, and only a line longer than a whole page is split, into full pages of it.
The pages, joined, are the file's text exactly: nothing is ever cut (ADR-0075). The text is
instruction from the person's locked bundle (Decision 3, R11), so it carries no data marker.

An unknown name, a page out of range and a text that cannot be read now are each a
`SkillShelfError` naming the shelf's size and the page count, for the loop to hand back as a tool
error. Declared by `interfaces/skill_shelf_interface.py::SkillShelfInterface`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError
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
from vibey_runners.common.capabilities.plugin_command_index import PluginCommandIndex
from vibey_runners.common.capabilities.resolver import DESCRIPTION_MAX_CHARS
from vibey_runners.common.capabilities.safe_text import SafeText
from vibey_runners.common.capabilities.shelf_entry import ShelfEntry
from vibey_runners.common.capabilities.shelf_page import ShelfPage
from vibey_runners.common.capabilities.shelf_text import ShelfText
from vibey_runners.common.capabilities.skill_index import SKILL_MAX_BYTES, SkillIndex
from vibey_runners.common.capabilities.skill_shelf_error import SkillShelfError

MIN_ANSWER_CHARS: Final = 512
"""The smallest answer budget a page is cut to: room for the longest name-only entry (a
257-character qualified name and its keys, about 310 characters) with margin. The smallest budget
a loop passes is far above it (`[loops] capability_answer_tokens` is at least 256 tokens)."""
_EMPTY_LIST: Final = len("[]")
_SEPARATOR: Final = len(", ")
"""`json.dumps`'s default item separator."""


class SkillShelf:
    """Declared by `interfaces/skill_shelf_interface.py::SkillShelfInterface`."""

    def __init__(
        self,
        entries: Sequence[ShelfEntry],
        skipped: Sequence[tuple[Path, str]],
        reader: FileReaderInterface,
    ) -> None:
        self._entries = tuple(entries)
        self._skipped = tuple(skipped)
        self._reader = reader
        self._by_name = {entry.name: entry for entry in self._entries}

    @classmethod
    def of(
        cls,
        document: SnapshotDocumentInterface,
        *,
        skills: SkillIndexInterface | None = None,
        commands: PluginCommandIndexInterface | None = None,
        text: SafeTextInterface | None = None,
        reader: FileReaderInterface | None = None,
    ) -> SkillShelf:
        safe = text or SafeText()
        catalog = (skills or SkillIndex()).build(document.plugin_dirs)
        found = {f"{entry.plugin}:{entry.name}": entry for entry in catalog.skills}
        folders = {path.name: path for path in document.plugin_dirs}
        entries: list[ShelfEntry] = []
        skipped = list(catalog.skipped)
        for qualified in document.skills:
            skill = found.get(qualified)
            if skill is None:
                plugin = qualified.split(":", 1)[0]
                skipped.append(
                    (
                        folders.get(plugin, Path(plugin)),
                        f"the run's document names the skill {qualified}, which its plugin no "
                        "longer holds",
                    )
                )
                continue
            description = safe.clean(skill.description, DESCRIPTION_MAX_CHARS)
            entries.append(ShelfEntry(qualified, "skill", description, skill.path))
        names = {entry.name for entry in entries}
        indexed, command_skipped = (commands or PluginCommandIndex()).build(document.plugin_dirs)
        skipped.extend(command_skipped)
        for command in indexed:
            qualified = f"{command.plugin}:{command.name}"
            if qualified in names:
                skipped.append(
                    (
                        command.path,
                        f"is the command {qualified}, which a skill of that name already is",
                    )
                )
                continue
            entries.append(ShelfEntry(qualified, "command", command.description, command.path))
        return cls(entries, skipped, reader or BoundedFileReader())

    @property
    def entries(self) -> tuple[ShelfEntry, ...]:
        return self._entries

    @property
    def skipped(self) -> tuple[tuple[Path, str], ...]:
        return self._skipped

    def page(self, number: int, answer_chars: int) -> ShelfPage:
        pages = self._pages(answer_chars)
        if not 1 <= number <= len(pages):
            raise SkillShelfError(
                f"there is no page {number} of this run's shelf of {self._size()}; "
                f"it has {_count(len(pages), 'page')}"
            )
        return ShelfPage(pages[number - 1], number, len(pages))

    def read(self, name: str, number: int, answer_chars: int) -> ShelfText:
        _floor(answer_chars)
        entry = self._by_name.get(name)
        if entry is None:
            listed = len(self._pages(answer_chars))
            raise SkillShelfError(
                f"there is no skill or command {name!r} on this run's shelf of {self._size()} "
                f"(skills_list shows them on {_count(listed, 'page')})"
            )
        try:
            text = self._reader.read_text(entry.path, SKILL_MAX_BYTES)
        except FileTooLargeError:
            raise SkillShelfError(
                f"{name!r} cannot be read now: it is larger than {SKILL_MAX_BYTES} bytes"
            ) from None
        except UnicodeDecodeError:
            raise SkillShelfError(f"{name!r} cannot be read now: it is not UTF-8") from None
        except OSError as exc:
            raise SkillShelfError(f"{name!r} cannot be read now: {exc}") from None
        pages = self._split(text, answer_chars)
        if not 1 <= number <= len(pages):
            raise SkillShelfError(
                f"there is no page {number} of {name!r} on this run's shelf of {self._size()}; "
                f"it has {_count(len(pages), 'page')}"
            )
        return ShelfText(name, entry.kind, number, len(pages), pages[number - 1])

    def _size(self) -> str:
        return _count(len(self._entries), "entry", "entries")

    def _pages(self, answer_chars: int) -> list[tuple[ShelfEntry, ...]]:
        """The shelf in pages whose JSON is at most `answer_chars`; always at least one."""
        _floor(answer_chars)
        pages: list[tuple[ShelfEntry, ...]] = []
        current: list[ShelfEntry] = []
        size = _EMPTY_LIST
        for entry in self._entries:
            shown = entry
            item = len(_item(shown))
            if _EMPTY_LIST + item > answer_chars:  # too long for any page: its name only
                shown = replace(entry, description="")
                item = len(_item(shown))
            added = item + (_SEPARATOR if current else 0)
            if current and size + added > answer_chars:
                pages.append(tuple(current))
                current, size, added = [], _EMPTY_LIST, item
            current.append(shown)
            size += added
        pages.append(tuple(current))
        return pages

    @staticmethod
    def _split(text: str, answer_chars: int) -> list[str]:
        """`text` in pages of at most `answer_chars` characters, broken at line ends where a
        line fits; joined, they are `text`. Always at least one page."""
        pages: list[str] = []
        current = ""
        for line in text.splitlines(keepends=True):
            if len(current) + len(line) <= answer_chars:
                current += line
                continue
            if current:
                pages.append(current)
            while len(line) > answer_chars:  # a line no page holds: full pages of it
                pages.append(line[:answer_chars])
                line = line[answer_chars:]
            current = line
        pages.append(current)
        return pages


def _item(entry: ShelfEntry) -> str:
    """One entry as the list's JSON holds it. A module-level function: a pure rendering shared by
    the shelf's paging and nothing else, with no state to hold."""
    return json.dumps({"name": entry.name, "kind": entry.kind, "description": entry.description})


def _count(number: int, singular: str, plural: str | None = None) -> str:
    """`1 page`, `2 pages`. A module-level function: pure wording, no state to hold."""
    return f"{number} {singular if number == 1 else (plural or singular + 's')}"


def _floor(answer_chars: int) -> None:
    """Refuses an answer budget below `MIN_ANSWER_CHARS`. A module-level function: one check that
    `page` and `read` share, with no state to hold."""
    if answer_chars < MIN_ANSWER_CHARS:
        raise ValueError(
            f"an answer budget must be at least {MIN_ANSWER_CHARS} characters, not {answer_chars}"
        )
