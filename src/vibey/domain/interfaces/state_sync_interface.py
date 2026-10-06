# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the state sync.

Mirrors `vibey/domain/state_sync.py` (ADR-0016, ADR-0086). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.state_sync import (
        Exported,
        JsonValue,
        MergeOutcome,
        Row,
        Snapshot,
        SnapshotDiff,
        TableSpec,
    )


@runtime_checkable
class CanonicalJsonInterface(Protocol):
    """One encoding per JSON value, with numbers kept exact."""

    def dumps(self, value: JsonValue) -> str: ...

    def loads(self, text: str | bytes) -> JsonValue: ...


@runtime_checkable
class SnapshotCodecInterface(Protocol):
    """Builds snapshots from rows, and reads and writes their canonical document."""

    @property
    def specs(self) -> tuple[TableSpec, ...]: ...

    def key(self, spec: TableSpec, row: Row) -> str: ...

    def build(self, schema: Iterable[str], tables: Mapping[str, Iterable[Row]]) -> Snapshot: ...

    def encode(self, snapshot: Snapshot) -> bytes: ...

    def digest(self, snapshot: Snapshot) -> str: ...

    def decode(self, data: bytes) -> Snapshot: ...

    def encode_export(self, exported: Exported) -> bytes: ...

    def decode_export(self, data: bytes) -> Exported: ...


@runtime_checkable
class StateMergerInterface(Protocol):
    """Merges two ends' snapshots against the one they last agreed on."""

    def merge(
        self, base: Snapshot | None, mine: Snapshot, theirs: Snapshot | None
    ) -> MergeOutcome: ...


@runtime_checkable
class SnapshotDifferInterface(Protocol):
    """What changes one snapshot into another."""

    def diff(self, before: Snapshot, after: Snapshot) -> SnapshotDiff: ...


@runtime_checkable
class ConflictRulesInterface(Protocol):
    """Reads `table=rule` overrides onto the synced tables."""

    def apply(self, text: str, specs: Sequence[TableSpec] = ...) -> tuple[TableSpec, ...]: ...
