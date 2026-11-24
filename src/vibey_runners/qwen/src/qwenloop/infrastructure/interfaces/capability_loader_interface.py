# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for applying a run's capability snapshot to the local runner (SP-LOOPS Phase 5,
Task 8; R3, R8, R9, R12)."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.interfaces.skill_shelf_interface import (
    SkillShelfInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.listing_text import ListingForm


@runtime_checkable
class LoadedCapabilitiesInterface(Protocol):
    """What one run is given from its snapshot."""

    @property
    def document(self) -> SnapshotDocumentInterface:
        """The document, as the strict reader returned it."""
        ...

    @property
    def shelf(self) -> SkillShelfInterface:
        """The skills and plugin commands the run may read on demand."""
        ...

    @property
    def prompt(self) -> str:
        """The capability block of the system prompt: the listing, then the repository's
        instruction files. Its estimated tokens are at most `[loops] capability_prompt_tokens`."""
        ...

    @property
    def listing_form(self) -> ListingForm:
        """The form the listing took: `full`, `names` or `count`."""
        ...

    @property
    def instruction_files(self) -> tuple[str, ...]:
        """The instruction files inlined whole in `prompt`, by name."""
        ...

    @property
    def notices(self) -> tuple[str, ...]:
        """What the operator is told about the snapshot that the run cannot honour."""
        ...

    def event(self) -> dict[str, object]:
        """The `capabilities.applied` event: the digest, counts, the listing's form, the names
        of the inlined files and the notices. Never a file's text, never an environment value."""
        ...


@runtime_checkable
class CapabilityLoaderInterface(Protocol):
    def load(self, path: Path, *, cwd: Path) -> LoadedCapabilitiesInterface:
        """The run's snapshot from the document at `path`, for a run in `cwd`. Raises
        `CapabilityRefused`, naming only `path`, when the document is refused or cannot be read;
        the run then does not start."""
        ...
