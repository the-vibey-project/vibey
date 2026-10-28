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

from collections.abc import Iterator, Mapping, Sequence
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


@dataclass(frozen=True)
class Break:
    """One place a snapshot stopped being what its manifest and its seals say it is.

    `forge_class` is the class file it was found in, or `manifest` for the manifest itself.
    `line` is the 1-based line of a record that fails its own checks, and `None` when the
    break is about a file as a whole (a removed last line, a missing file, a stale manifest).
    `kind` is one of `forge_snapshot.BREAK_KINDS`; `detail` is a sentence a person can act on.
    """

    forge_class: str
    line: int | None
    kind: str
    detail: str


@runtime_checkable
class BreakInterface(Protocol):
    @property
    def forge_class(self) -> str: ...

    @property
    def line(self) -> int | None: ...

    @property
    def kind(self) -> str: ...

    @property
    def detail(self) -> str: ...


STATE_FOUND = "found"
STATE_BEFORE_FIRST = "before-first-record"
STATE_UNKNOWN = "unknown-object"


@dataclass(frozen=True)
class StateAsOf:
    """What a snapshot says an object looked like at a moment, or why it cannot say.

    Three answers, never two: `found` carries the record; `before-first-record` means the
    object was recorded, but every record is later than the moment; `unknown-object` means
    the snapshot holds no record of it at all. None of them says the object did not exist or
    was deleted, because a snapshot sees neither: a record means "this state, first seen
    then". `last_capture` is when the most recent capture began, so a reader can see how
    stale "as of" is.
    """

    status: str
    native_id: str = ""
    record: Mapping[str, Any] | None = None
    last_capture: str | None = None


@runtime_checkable
class SnapshotQueryInterface(Protocol):
    """Reads a snapshot back in time. Read-only: it appends nothing and asks no forge."""

    def state(self, forge_class: str, native_id: str, as_of: str) -> StateAsOf:
        """The latest record of the object with `captured_at` at or before `as_of`.

        Raises `ValueError` for a moment that is not ISO 8601 and `SnapshotStoreError` for a
        class file that fails its seals, before any answer is given.
        """
        ...

    def issue(self, number: int, as_of: str) -> StateAsOf:
        """The same for the issue with this number, which is not its native id."""
        ...


@runtime_checkable
class SnapshotVerifierInterface(Protocol):
    """Walks a snapshot directory and reports every way it no longer matches itself."""

    def verify(self) -> tuple[Break, ...]:
        """Check every class file and the manifest, reading nothing from the forge.

        Reports the first break in each file, and the manifest-level breaks (a missing or
        foreign manifest, a head that does not match, a file the manifest names and does not
        have, a file it does not name). An empty tuple is a snapshot that is intact. Never
        raises for what is in the directory: a thing it cannot read is a `Break`.
        """
        ...


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

    def records(self, forge_class: str) -> Iterator[Mapping[str, Any]]:
        """Every record of the class in file order, each checked as the store checks it.

        Refuses the file at the first line that is not this store's own, unbroken record:
        a damaged chain is never read from.
        """
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


@runtime_checkable
class ForgeInventoryInterface(Protocol):
    """What each forge's API exposes, as a checked-in list the capture is accounted against.

    The capture knows the classes it reads and the ones it declines. It cannot know, from
    itself, whether those two lists cover what a forge offers; this is the third list that
    says so (#1571). A forge it holds no list for is unknown, never "nothing to account for".
    """

    @property
    def sha256(self) -> str:
        """The digest of the inventory as read, so a manifest names the list it was held to."""
        ...

    def classes(self, forge: str) -> tuple[str, ...] | None:
        """The forge-neutral classes the forge's API exposes, sorted; `None` if not inventoried."""
        ...

    def verified(self, forge: str) -> bool:
        """Whether the forge's list was read in full from its published API description."""
        ...
