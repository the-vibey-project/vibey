# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of a forge snapshot (vibey ADR-0016): read the forge, keep the records, run one.

A snapshot is three jobs that change for different reasons, so each has its own seam. The
READER asks one forge about one artifact class and says what it found — or, never the same
thing, that it could not look. The STORE keeps what was found as append-only, hash-chained
records and knows where each chain stands. The SNAPSHOT runs the capture: which classes,
from which moment, and the manifest that says what happened to every class, including the
ones nobody captured.

Splitting them is what lets the later slices of vibey#136 land without touching the rest: a
second forge is a second reader, and the vibey ledger writer is a second store.

The three records below are the shapes those seams speak in. They are declared here rather
than in `vibey_gh.forge_snapshot` so the interface names them without importing the module
that implements it: naming a shape is declaring, not consuming.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# One artifact as the forge returned it: its native id, and its native JSON, verbatim.
type Observation = tuple[str, Mapping[str, Any]]


@dataclass(frozen=True)
class ForgeRead:
    """What one walk of one artifact class found, or why it could not look.

    `problem` is empty exactly when the forge answered. A class the forge could not be asked
    about carries no observations and a sentence saying why, so that "could not look" can
    never be written down as "there was nothing".

    `high_water` is the latest update time among what was walked, in the forge's own clock,
    for a class that can be resumed from a moment; `None` for one that cannot, or when the
    walk returned nothing.
    """

    forge_class: str
    native_class: str
    observations: tuple[Observation, ...] = ()
    high_water: str | None = None
    problem: str = ""


@runtime_checkable
class ForgeReadInterface(Protocol):
    @property
    def forge_class(self) -> str: ...

    @property
    def native_class(self) -> str: ...

    @property
    def observations(self) -> tuple[Observation, ...]: ...

    @property
    def high_water(self) -> str | None: ...

    @property
    def problem(self) -> str: ...


@dataclass(frozen=True)
class ChainHead:
    """Where one class's chain stands: how many records it holds, and the digest of the last."""

    records: int
    head: str | None


@runtime_checkable
class ChainHeadInterface(Protocol):
    @property
    def records(self) -> int: ...

    @property
    def head(self) -> str | None: ...


@dataclass(frozen=True)
class AppendOutcome:
    """What one append did: records written, observations already recorded, the new head."""

    appended: int
    unchanged: int
    records: int
    head: str | None


@runtime_checkable
class AppendOutcomeInterface(Protocol):
    @property
    def appended(self) -> int: ...

    @property
    def unchanged(self) -> int: ...

    @property
    def records(self) -> int: ...

    @property
    def head(self) -> str | None: ...


@runtime_checkable
class ForgeReaderInterface(Protocol):
    """Reads one forge's artifact classes for one repository. Never writes to the forge."""

    forge: str
    repository: str

    def read(self, forge_class: str, since: str | None) -> ForgeRead:
        """Walk one class, every page of it, and return what the forge said.

        `since` is an ISO 8601 UTC moment, or `None` for everything. A class that can be
        filtered by update time is filtered by it; one that cannot is walked whole, and the
        store's content digest keeps the records it had already seen from being written
        twice. Never raises for anything the forge does: a missing client, a failed call or
        an answer of the wrong shape all come back as `ForgeRead.problem`. An unknown class
        name is the caller's mistake and raises `ValueError`.
        """
        ...


@runtime_checkable
class SnapshotStoreInterface(Protocol):
    """Keeps the records of one repository on one forge, each class its own hash chain."""

    def manifest(self) -> Mapping[str, Any] | None:
        """The manifest the last completed capture left, or `None` when there is none.

        Refuses a manifest written for a different forge or repository: a snapshot holds
        one repository, and appending a second to its chains would corrupt both.
        """
        ...

    def chain(self, forge_class: str) -> ChainHead:
        """Where the class's chain stands, loading and checking its records the first time.

        Refuses a file holding anything but this store's own records for that class.
        """
        ...

    def append(
        self,
        forge_class: str,
        native_class: str,
        captured_at: str,
        observations: Sequence[Observation],
    ) -> AppendOutcome:
        """Append one record per observation whose payload differs from the one recorded last.

        Each record links to the one before it in the class, so the chain continues across
        captures. An observation identical to the latest record for the same native object
        is counted as unchanged and not written: a capture repeated over the same moment
        appends nothing, which is what makes a rerun safe.
        """
        ...

    def write_manifest(self, manifest: Mapping[str, Any]) -> Path:
        """Replace the manifest, whole or not at all, and return where it is."""
        ...


@runtime_checkable
class ForgeSnapshotInterface(Protocol):
    """Runs one capture of a forge into a store and accounts for every artifact class."""

    def capture(
        self,
        *,
        classes: Sequence[str] | None = None,
        since: str | None = None,
    ) -> Mapping[str, Any]:
        """Capture the selected classes, write the manifest, and return it.

        `classes` names forge-neutral classes; `None` is every class this snapshot supports.
        `since` is an ISO 8601 moment, `"resume"` for the resume point the last manifest
        recorded, or `None` for a full capture. Raises `ValueError` for an unknown class, an
        empty selection or an unreadable moment, before anything is read or written.
        """
        ...
