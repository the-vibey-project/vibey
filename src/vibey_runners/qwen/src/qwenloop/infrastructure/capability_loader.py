# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run's capability snapshot, as the local runner applies it (SP-LOOPS Phase 5, Task 8; R3, R8,
R9, R12; Review Focus 4 and 5).

`gptossloop run --capabilities PATH` and `qwenloop run --capabilities PATH` read the document the
conductor wrote through the family's strict store (R3). A document that is refused, or cannot be
read, is a `CapabilityRefused` naming only its path -- the message reaches the console and the
conductor's gate, and a tampered document must not put its own text there -- and the command
exits 78 before any model is started or called.

From the document come the run's skill shelf (its skills and plugin commands, read on demand) and
the capability block of its system prompt, held to `[loops] capability_prompt_tokens`:

- the listing first (R9): in full, by name, or counted, whichever form first fits;
- then the repository's instruction files (R12), each inlined whole or named with its size, never
  cut, in what the listing leaves.

The listing keeps room to name every instruction file that exists, so a file is never silently
left out and the two together never overrun the budget; it degrades to make that room. Should
even the counted listing leave too little to name them all (many long names in the smallest
budget), the files are counted on one line that sends the agent to `[loops] instruction_files`.

An input folder (`folders`) outside the worktree is a notice, never a grant: this loop's file
tools stay inside the worktree. Declared by
`interfaces/capability_loader_interface.py::CapabilityLoaderInterface`.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.capability_listing import CapabilityListing
from vibey_runners.common.capabilities.instruction_files import (
    InstructionFileReader,
    InstructionText,
)
from vibey_runners.common.capabilities.interfaces.capability_listing_interface import (
    CapabilityListingInterface,
)
from vibey_runners.common.capabilities.interfaces.instruction_file_reader_interface import (
    InstructionFileReaderInterface,
    InstructionTextInterface,
)
from vibey_runners.common.capabilities.interfaces.plugin_command_index_interface import (
    PluginCommandIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.skill_index_interface import (
    SkillIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.skill_shelf_interface import (
    SkillShelfInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_store_interface import (
    SnapshotDocumentStoreInterface,
)
from vibey_runners.common.capabilities.listing_text import ListingForm, ListingText
from vibey_runners.common.capabilities.skill_shelf import SkillShelf
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore
from vibey_runners.common.capabilities.token_estimate import TOKEN_ESTIMATE

JOINER: Final = "\n\n"
"""What separates the listing from the instruction files, and the block from the prompt."""
REFUSED: Final = (
    "the capability document {path} was refused or could not be read; "
    "the run does not start without it"
)
OUTSIDE_WORKTREE: Final = (
    "{folder} is outside the worktree and this loop's file tools cannot reach it"
)
TOO_MANY_TO_NAME: Final = (
    "{count} repository instruction files are too many to name in this loop's standing context "
    "([loops] capability_prompt_tokens); [loops] instruction_files names them: read them from "
    "the repository before you start."
)


class CapabilityRefused(Exception):
    """The run's capability document was refused or could not be read. The message names the
    document's path and nothing it holds; the cause is chained for a debugger."""


@dataclass(frozen=True, slots=True)
class LoadedCapabilities:
    """Declared by `interfaces/capability_loader_interface.py::LoadedCapabilitiesInterface`."""

    document: SnapshotDocumentInterface
    shelf: SkillShelfInterface
    prompt: str
    listing_form: ListingForm
    instruction_files: tuple[str, ...]
    notices: tuple[str, ...]

    def event(self) -> dict[str, object]:
        skills = sum(1 for entry in self.shelf.entries if entry.kind == "skill")
        return {
            "type": "capabilities.applied",
            "digest": self.document.digest,
            "plugins": len(self.document.plugin_dirs),
            "skills": skills,
            "commands": len(self.shelf.entries) - skills,
            "mcp_servers": len(self.document.mcp_servers),
            "listing": self.listing_form,
            "instruction_files": list(self.instruction_files),
            "notices": list(self.notices),
        }


class CapabilityLoader:
    """Declared by `interfaces/capability_loader_interface.py::CapabilityLoaderInterface`."""

    def __init__(
        self,
        store: SnapshotDocumentStoreInterface | None = None,
        listing: CapabilityListingInterface | None = None,
        instructions: InstructionFileReaderInterface | None = None,
        *,
        skills: SkillIndexInterface | None = None,
        commands: PluginCommandIndexInterface | None = None,
    ) -> None:
        self._store = store or SnapshotDocumentStore()
        self._listing = listing or CapabilityListing()
        self._instructions = instructions or InstructionFileReader()
        # The shelf's own two seams, passed through: how its plugin copies are indexed.
        self._skills = skills
        self._commands = commands

    def load(self, path: Path, *, cwd: Path) -> LoadedCapabilities:
        try:
            document = self._store.read(path)
            shelf = SkillShelf.of(document, skills=self._skills, commands=self._commands)
        except (SnapshotDocumentError, OSError) as exc:
            raise CapabilityRefused(REFUSED.format(path=path)) from exc
        listing, instructions = self._standing(document, shelf, cwd)
        return LoadedCapabilities(
            document=document,
            shelf=shelf,
            prompt=JOINER.join(part for part in (listing.text, instructions.text) if part),
            listing_form=listing.form,
            instruction_files=instructions.inlined,
            notices=self._notices(document, cwd),
        )

    def _standing(
        self, document: SnapshotDocumentInterface, shelf: SkillShelfInterface, cwd: Path
    ) -> tuple[ListingText, InstructionTextInterface]:
        """The listing and the instruction files, together at most the standing budget.

        `named` -- every file that exists named, none inlined -- is the least the files can
        take. The listing keeps that much free (its reserve), so what it leaves is at least
        `named`; the files then inline whole blocks in what is left beyond `named`, which keeps
        room for the lines of any file after the last one inlined, as none is longer than in
        `named`. The listing is always given the full budget, never a reduced one."""
        budget = document.capability_prompt_tokens
        names, max_bytes = document.instruction_files, document.instruction_max_bytes
        named = self._instructions.read(cwd, names, max_bytes, budget_chars=0)
        entries, servers = shelf.entries, document.mcp_servers
        if not named.text:  # no instruction file exists: the listing has the budget
            return self._listing.render(entries, servers, budget), named
        try:
            listing = self._listing.render(
                entries, servers, budget, reserve_tokens=TOKEN_ESTIMATE.tokens(JOINER + named.text)
            )
        except ValueError:  # not even the counted listing leaves room to name every file
            pass
        else:
            left = TOKEN_ESTIMATE.chars(budget) - len(listing.text)
            left -= len(JOINER) if listing.text else 0
            if left >= len(named.text):  # always, unless an empty listing left the whole budget
                return listing, self._instructions.read(
                    cwd, names, max_bytes, budget_chars=left - len(named.text)
                )
        counted = InstructionText(TOO_MANY_TO_NAME.format(count=len(named.named)), (), named.named)
        listing = self._listing.render(
            entries, servers, budget, reserve_tokens=TOKEN_ESTIMATE.tokens(JOINER + counted.text)
        )
        return listing, counted

    @staticmethod
    def _notices(document: SnapshotDocumentInterface, cwd: Path) -> tuple[str, ...]:
        """One notice per input folder outside `cwd`, both resolved. The tools are not widened."""
        worktree = Path(os.path.realpath(cwd))
        return tuple(
            OUTSIDE_WORKTREE.format(folder=folder)
            for folder in document.folders
            if not Path(os.path.realpath(folder)).is_relative_to(worktree)
        )
