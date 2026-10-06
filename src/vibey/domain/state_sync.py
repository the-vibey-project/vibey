# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The state sync: one vibey database's rows, kept the same at both ends (ADR-0086).

`vibey state sync` keeps a local database and an encrypted copy of it on the repository's
`vibey-state` branch the same, in both directions. This module is the pure half: what a
snapshot of the database is, how three of them merge, and what changes one into another.
Reading the database, the branch and the key is infrastructure's.

**Snapshot.** Every synced table's rows, each row a JSON object exactly as PostgreSQL's
`to_jsonb` renders it, keyed by its primary key; and the migrations the database has
applied. Numbers stay exact (`Decimal`, never `float`), and a snapshot has one canonical
encoding, so two equal snapshots are equal bytes and a digest says whether anything changed.

**Merge.** Three-way, against the snapshot both ends last agreed on (the base). A row only
one end changed takes that end's change; a row both ends changed to the same thing takes
it; a row both ends changed differently is resolved by its table's declared rule:
`newest` (by a declared timestamp column), `mine`, `theirs` or `refuse`. The ledger is never
resolved by a rule: its rows are append-only and its hash chain runs over `seq`, so two
ends that appended different events at the same `seq` have diverged, and the merge says so
and changes nothing (10.f: no silent partial).

**Idempotent.** Merging a database with the branch it just synced with changes nothing at
either end; a second run finds nothing to pull and nothing to push.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final, cast

from vibey.domain.errors import VibeyError

#: A value in a row: what JSON holds, with numbers kept exact.
type JsonValue = None | bool | int | Decimal | str | list[JsonValue] | dict[str, JsonValue]
type Row = Mapping[str, JsonValue]

#: The snapshot document's format, and the export file's (a snapshot with its base).
FORMAT: Final = "vibey-state/1"
EXPORT_FORMAT: Final = "vibey-state-export/1"


class StateSyncRefused(VibeyError):
    """The sync cannot go on without someone deciding something: it changed nothing."""


class SchemaMismatch(StateSyncRefused):
    """The two ends have applied different migrations: migrate first, then sync."""


class SnapshotUnreadable(StateSyncRefused):
    """A snapshot document is not one this vibey reads, or the key does not open it."""


class StateMoved(VibeyError):
    """The database changed under a sync between reading it and writing it: read again."""


class RemoteMoved(VibeyError):
    """The branch moved under a sync between reading it and pushing to it: read again."""


class ConflictRule(StrEnum):
    """What a row two ends changed differently becomes."""

    NEWEST = "newest"
    MINE = "mine"
    THEIRS = "theirs"
    REFUSE = "refuse"


@dataclass(frozen=True)
class TableSpec:
    """One synced table: its key, its conflict rule, and what applying it needs.

    `newest_by` is the timestamp column `ConflictRule.NEWEST` compares; `deferred` are
    columns that reference rows of the same table, written once every row is in;
    `sequences` are `(column, sequence)` pairs the sequence must be advanced past."""

    name: str
    key: tuple[str, ...]
    rule: ConflictRule = ConflictRule.REFUSE
    newest_by: str = ""
    append_only: bool = False
    deferred: tuple[str, ...] = ()
    sequences: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError(f"table {self.name!r} needs a key")
        if self.rule is ConflictRule.NEWEST and not self.newest_by:
            raise ValueError(f"table {self.name!r}: the newest rule needs newest_by")
        if self.append_only and self.rule is not ConflictRule.REFUSE:
            raise ValueError(f"table {self.name!r} is append-only: its rule is refuse")

    def with_rule(self, rule: ConflictRule) -> TableSpec:
        """This table under another rule; refuses one its table cannot take."""
        return TableSpec(
            self.name,
            self.key,
            rule,
            self.newest_by,
            self.append_only,
            self.deferred,
            self.sequences,
        )


#: Every synced table, parents before children: the order rows are written in, and the
#: reverse of the order they are deleted in. A table the migrations add and this list
#: does not name fails `tests/infrastructure/db/test_state_store.py`.
TABLES: Final[tuple[TableSpec, ...]] = (
    TableSpec("project", ("id",), ConflictRule.NEWEST, "updated_at"),
    TableSpec("event", ("project_id", "seq"), append_only=True),
    TableSpec(
        "job",
        ("id",),
        ConflictRule.NEWEST,
        "updated_at",
        sequences=(("bump_seq", "job_bump_seq"),),
    ),
    TableSpec("job_dependency", ("job_id", "depends_on_job_id")),
    TableSpec("work_item", ("project_id", "cycle", "item_id")),
    TableSpec("open_item", ("item_id",), deferred=("superseded_by",)),
    TableSpec("handoff", ("handoff_id",)),
    TableSpec("engine_health", ("project_id", "engine_id"), ConflictRule.MINE),
    TableSpec("rotation_cursor", ("project_id", "engine_id"), ConflictRule.MINE),
    TableSpec("human_gate", ("gate_id",), ConflictRule.NEWEST, "answered_at"),
    TableSpec("artifact", ("artifact_id",)),
    TableSpec("budget_ledger", ("project_id", "cycle", "phase", "engine_id")),
    TableSpec(
        "triaged_ticket",
        ("repository", "issue_number"),
        ConflictRule.NEWEST,
        "updated_at",
        sequences=(("bump_seq", "triaged_ticket_bump_seq"),),
    ),
)

#: Tables in the database that are never synced, each for its reason: the migrator owns
#: its own record, the next `seq` is derived from the ledger it numbers, and the sync's
#: own watermark says where *this* database stands, which no other one shares.
NOT_SYNCED: Final[frozenset[str]] = frozenset({"schema_migration", "event_seq", "state_sync"})


class CanonicalJson:
    """One encoding per value: keys sorted, no spaces, ASCII, numbers exact.

    The ledger's `canonical_bytes` renders a `Decimal` as a quoted string, which would turn
    a `numeric` cost or a number inside an event's payload into text on the way through;
    this keeps every number the number PostgreSQL wrote."""

    def dumps(self, value: JsonValue) -> str:
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError(f"{value} has no JSON form")
            return str(value)
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, list):
            return "[" + ",".join(self.dumps(item) for item in value) + "]"
        if isinstance(value, dict):
            return (
                "{"
                + ",".join(json.dumps(k) + ":" + self.dumps(value[k]) for k in sorted(value))
                + "}"
            )
        raise TypeError(f"{type(value).__name__} is not a JSON value")

    def loads(self, text: str | bytes) -> JsonValue:
        """JSON text as values, every number with a fraction or exponent a `Decimal`."""
        loaded: JsonValue = json.loads(text, parse_float=Decimal)
        return loaded


CANONICAL: Final = CanonicalJson()


@dataclass(frozen=True)
class Snapshot:
    """Every synced row of one database, and the migrations it has applied.

    `tables` maps a table's name to its rows, each keyed by the canonical encoding of its
    primary key's values."""

    schema: tuple[str, ...]
    tables: Mapping[str, Mapping[str, Row]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A table with no rows and a table not named are the same state.
        object.__setattr__(
            self, "tables", {name: rows for name, rows in self.tables.items() if rows}
        )

    def rows(self, table: str) -> Mapping[str, Row]:
        return self.tables.get(table, {})

    @property
    def row_count(self) -> int:
        return sum(len(rows) for rows in self.tables.values())


@dataclass(frozen=True)
class Exported:
    """A snapshot carried to another database, with the commit it was last synced with."""

    snapshot: Snapshot
    remote: str
    base: str | None


class SnapshotCodec:
    """Builds snapshots from rows, and reads and writes their one canonical document."""

    def __init__(self, specs: Sequence[TableSpec] = TABLES) -> None:
        self._specs = tuple(specs)

    @property
    def specs(self) -> tuple[TableSpec, ...]:
        return self._specs

    def key(self, spec: TableSpec, row: Row) -> str:
        missing = [column for column in spec.key if column not in row]
        if missing:
            raise SnapshotUnreadable(f"a {spec.name} row has no {', '.join(missing)}")
        return CANONICAL.dumps([row[column] for column in spec.key])

    def build(self, schema: Iterable[str], tables: Mapping[str, Iterable[Row]]) -> Snapshot:
        """A snapshot of these rows. A table this codec does not sync is refused."""
        known = {spec.name: spec for spec in self._specs}
        unknown = sorted(set(tables) - set(known))
        if unknown:
            raise SnapshotUnreadable(f"tables this vibey does not sync: {', '.join(unknown)}")
        built: dict[str, dict[str, Row]] = {}
        for name, rows in tables.items():
            keyed: dict[str, Row] = {}
            for row in rows:
                key = self.key(known[name], row)
                if key in keyed:
                    raise SnapshotUnreadable(f"two {name} rows share the key {key}")
                keyed[key] = row
            if keyed:
                built[name] = keyed
        return Snapshot(tuple(schema), built)

    def document(self, snapshot: Snapshot) -> dict[str, JsonValue]:
        tables: dict[str, JsonValue] = {}
        for spec in self._specs:
            rows = snapshot.rows(spec.name)
            if rows:
                tables[spec.name] = [dict(rows[key]) for key in sorted(rows)]
        return {"format": FORMAT, "schema": list(snapshot.schema), "tables": tables}

    def encode(self, snapshot: Snapshot) -> bytes:
        return CANONICAL.dumps(self.document(snapshot)).encode()

    def digest(self, snapshot: Snapshot) -> str:
        return hashlib.sha256(self.encode(snapshot)).hexdigest()

    def decode(self, data: bytes) -> Snapshot:
        try:
            document = CANONICAL.loads(data)
        except ValueError as bad:
            raise SnapshotUnreadable(f"the snapshot is not JSON: {bad}") from bad
        return self._from_document(document)

    def _from_document(self, document: JsonValue) -> Snapshot:
        if not isinstance(document, dict) or document.get("format") != FORMAT:
            raise SnapshotUnreadable(f"not a {FORMAT} snapshot")
        schema, tables = document.get("schema"), document.get("tables")
        if not isinstance(schema, list) or not all(isinstance(v, str) for v in schema):
            raise SnapshotUnreadable("the snapshot's schema is not a list of migrations")
        if not isinstance(tables, dict):
            raise SnapshotUnreadable("the snapshot's tables are not an object")
        rows: dict[str, list[Row]] = {}
        for name, listed in tables.items():
            if not isinstance(listed, list) or not all(isinstance(r, dict) for r in listed):
                raise SnapshotUnreadable(f"the snapshot's {name} rows are not objects")
            rows[name] = cast(list[Row], listed)
        return self.build([str(v) for v in schema], rows)

    def encode_export(self, exported: Exported) -> bytes:
        return CANONICAL.dumps(
            {
                "format": EXPORT_FORMAT,
                "remote": exported.remote,
                "base": exported.base,
                "state": self.document(exported.snapshot),
            }
        ).encode()

    def decode_export(self, data: bytes) -> Exported:
        try:
            document = CANONICAL.loads(data)
        except ValueError as bad:
            raise SnapshotUnreadable(f"the export is not JSON: {bad}") from bad
        if not isinstance(document, dict) or document.get("format") != EXPORT_FORMAT:
            raise SnapshotUnreadable(f"not a {EXPORT_FORMAT} file")
        remote, base = document.get("remote"), document.get("base")
        if not isinstance(remote, str) or not (base is None or isinstance(base, str)):
            raise SnapshotUnreadable("the export does not say which remote it came from")
        return Exported(self._from_document(document.get("state")), remote, base)


@dataclass(frozen=True)
class Conflict:
    """A row two ends changed differently that its table's rule could not settle."""

    table: str
    key: str
    reason: str

    def describe(self) -> str:
        return f"{self.table} {self.key}: {self.reason}"


@dataclass(frozen=True)
class MergeOutcome:
    """The merged snapshot, and every conflict. With any conflict, nothing is applied."""

    merged: Snapshot
    conflicts: tuple[Conflict, ...] = ()


class StateMerger:
    """The three-way merge. Declared by
    `interfaces/state_sync_interface.py::StateMergerInterface`."""

    def __init__(self, specs: Sequence[TableSpec] = TABLES) -> None:
        self._specs = tuple(specs)

    def merge(self, base: Snapshot | None, mine: Snapshot, theirs: Snapshot | None) -> MergeOutcome:
        """Merge `mine` and `theirs` against `base`; None is a snapshot with no rows."""
        if theirs is not None and theirs.schema != mine.schema:
            raise SchemaMismatch(
                "the two ends have applied different migrations "
                f"(here: {(mine.schema or ('none',))[-1]}, "
                f"there: {(theirs.schema or ('none',))[-1]}): "
                "run `vibey migrate` on the one behind, then sync"
            )
        empty = Snapshot(mine.schema)
        base_, theirs_ = base or empty, theirs or empty
        tables: dict[str, dict[str, Row]] = {}
        conflicts: list[Conflict] = []
        for spec in self._specs:
            b, m, t = base_.rows(spec.name), mine.rows(spec.name), theirs_.rows(spec.name)
            merged: dict[str, Row] = {}
            for key in sorted(set(b) | set(m) | set(t)):
                row, reason = self._row(spec, b.get(key), m.get(key), t.get(key))
                if reason:
                    conflicts.append(Conflict(spec.name, key, reason))
                if row is not None:
                    merged[key] = row
            if merged:
                tables[spec.name] = merged
        return MergeOutcome(Snapshot(mine.schema, tables), tuple(conflicts))

    def _row(
        self, spec: TableSpec, b: Row | None, m: Row | None, t: Row | None
    ) -> tuple[Row | None, str]:
        if spec.append_only:
            return self._appended(b, m, t)
        if m == t:
            return m, ""
        if m == b:
            return t, ""
        if t == b:
            return m, ""
        if spec.rule is ConflictRule.MINE:
            return m, ""
        if spec.rule is ConflictRule.THEIRS:
            return t, ""
        if spec.rule is ConflictRule.NEWEST and m is not None and t is not None:
            newer = self._newer(m.get(spec.newest_by), t.get(spec.newest_by))
            if newer is not None:
                return (m if newer else t), ""
            return m, f"changed at both ends with the same {spec.newest_by}"
        if m is None or t is None:
            return m, "deleted at one end and changed at the other"
        return m, "changed differently at both ends"

    @staticmethod
    def _appended(b: Row | None, m: Row | None, t: Row | None) -> tuple[Row | None, str]:
        """A ledger row: present at either end, it is the same row at every end it is at."""
        if b is not None and (m != b or t != b):
            return m, "a ledger row was changed or removed: the ledger is append-only"
        if m is not None and t is not None and m != t:
            return m, (
                "the ledger diverged: the two ends appended different events at this seq; "
                "the hash chain runs over seq, so neither can be renumbered"
            )
        return (m if m is not None else t), ""

    @staticmethod
    def _newer(mine: JsonValue, theirs: JsonValue) -> bool | None:
        """Whether mine is the newer, None when neither is; a missing time is the oldest."""
        if mine == theirs:
            return None
        if mine is None or theirs is None:
            return theirs is None
        try:
            mine_at = datetime.fromisoformat(str(mine))
            theirs_at = datetime.fromisoformat(str(theirs))
        except ValueError:
            return None
        if (mine_at.tzinfo is None) != (theirs_at.tzinfo is None) or mine_at == theirs_at:
            # A time without its offset is not comparable with one that has it.
            return None
        return mine_at > theirs_at


@dataclass(frozen=True)
class RowChange:
    """One row going from `before` to `after`; None is the row's absence."""

    table: str
    key: str
    before: Row | None
    after: Row | None


@dataclass(frozen=True)
class SnapshotDiff:
    """What changes one snapshot into another, parents first."""

    changes: tuple[RowChange, ...] = ()

    @property
    def empty(self) -> bool:
        return not self.changes

    def count(self) -> int:
        return len(self.changes)


class SnapshotDiffer:
    """Declared by `interfaces/state_sync_interface.py::SnapshotDifferInterface`."""

    def __init__(self, specs: Sequence[TableSpec] = TABLES) -> None:
        self._specs = tuple(specs)

    def diff(self, before: Snapshot, after: Snapshot) -> SnapshotDiff:
        changes: list[RowChange] = []
        for spec in self._specs:
            old, new = before.rows(spec.name), after.rows(spec.name)
            for key in sorted(set(old) | set(new)):
                if old.get(key) != new.get(key):
                    changes.append(RowChange(spec.name, key, old.get(key), new.get(key)))
        return SnapshotDiff(tuple(changes))


@dataclass(frozen=True)
class RemoteHead:
    """The branch's head commit and the sealed snapshot it holds."""

    commit: str
    data: bytes


class SyncState(StrEnum):
    """Where a sync left the two ends, or where a status found them."""

    IN_SYNC = "in-sync"
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class SyncReport:
    """What a sync did, or what a status found to do."""

    state: SyncState
    remote: str
    pulled: int = 0
    pushed: bool = False
    to_push: bool = False
    commit: str | None = None
    rows: int = 0
    conflicts: tuple[Conflict, ...] = ()

    def describe(self) -> str:
        at = f" at {self.commit[:12]}" if self.commit else ""
        if self.state is SyncState.CONFLICT:
            return (
                f"{self.remote}: {len(self.conflicts)} conflict(s); nothing was changed at "
                "either end:\n" + "\n".join(f"  {c.describe()}" for c in self.conflicts)
            )
        if self.state is SyncState.IN_SYNC:
            return f"{self.remote}: in sync{at}, {self.rows} row(s)"
        push = "changes here to push" if self.to_push else "nothing to push"
        if self.state is SyncState.SYNCED:
            push = "pushed" if self.pushed else push
            return (
                f"{self.remote}: synced{at}: {self.pulled} row change(s) pulled, {push}; "
                f"{self.rows} row(s)"
            )
        return f"{self.remote}: {self.pulled} row change(s) to pull, {push}; {self.rows} row(s)"


class ConflictRules:
    """Reads a table-to-rule override list, `table=rule,table=rule`, onto the tables."""

    def apply(self, text: str, specs: Sequence[TableSpec] = TABLES) -> tuple[TableSpec, ...]:
        rules: dict[str, ConflictRule] = {}
        names = {spec.name for spec in specs}
        for item in (part.strip() for part in text.split(",")):
            if not item:
                continue
            table, equals, rule = (piece.strip() for piece in item.partition("="))
            if not equals or table not in names:
                raise ValueError(f"{item!r} is not table=rule for a synced table")
            try:
                rules[table] = ConflictRule(rule)
            except ValueError:
                raise ValueError(
                    f"{rule!r} is not a rule: one of {', '.join(r.value for r in ConflictRule)}"
                ) from None
        return tuple(
            spec.with_rule(rules[spec.name]) if spec.name in rules else spec for spec in specs
        )
