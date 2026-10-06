# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The state sync's pure half (ADR-0086): the snapshot, its one canonical encoding, the
three-way merge and its rules, the differ, the rule overrides and what a report says."""

from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest

from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.state_sync_interface import (
    CanonicalJsonInterface,
    ConflictRulesInterface,
    SnapshotCodecInterface,
    SnapshotDifferInterface,
    StateMergerInterface,
)
from vibey.domain.state_sync import (
    CANONICAL,
    EXPORT_FORMAT,
    FORMAT,
    NOT_SYNCED,
    TABLES,
    Conflict,
    ConflictRule,
    ConflictRules,
    Exported,
    JsonValue,
    RemoteMoved,
    Row,
    RowChange,
    SchemaMismatch,
    Snapshot,
    SnapshotCodec,
    SnapshotDiff,
    SnapshotDiffer,
    SnapshotUnreadable,
    StateMerger,
    StateMoved,
    StateSyncRefused,
    SyncReport,
    SyncState,
    TableSpec,
)

SCHEMA = ("0001_initial", "0002_more")

#: A small table set with one table per rule, in parent-first order.
SPECS = (
    TableSpec("dated", ("id",), ConflictRule.NEWEST, "updated_at"),
    TableSpec("ledger", ("project", "seq"), append_only=True),
    TableSpec("plain", ("id",)),
    TableSpec("ours", ("id",), ConflictRule.MINE),
    TableSpec("yours", ("id",), ConflictRule.THEIRS),
)
CODEC = SnapshotCodec(SPECS)


def snap(**tables: list[Row]) -> Snapshot:
    return CODEC.build(SCHEMA, tables)


def row(id_: int, value: str, at: JsonValue = None) -> Row:
    return {"id": id_, "value": value, "updated_at": at}


def event(seq: int, kind: str) -> Row:
    return {"project": "p", "seq": seq, "kind": kind}


# --- the contracts --------------------------------------------------------------------------


def test_each_satisfies_its_interface() -> None:
    assert isinstance(CANONICAL, CanonicalJsonInterface)
    assert isinstance(SnapshotCodec(), SnapshotCodecInterface)
    assert isinstance(StateMerger(), StateMergerInterface)
    assert isinstance(SnapshotDiffer(), SnapshotDifferInterface)
    assert isinstance(ConflictRules(), ConflictRulesInterface)


def test_every_refusal_is_a_vibey_error_and_the_retryable_ones_are_not_refusals() -> None:
    assert issubclass(SchemaMismatch, StateSyncRefused)
    assert issubclass(SnapshotUnreadable, StateSyncRefused)
    assert issubclass(StateSyncRefused, VibeyError)
    assert not issubclass(StateMoved, StateSyncRefused)
    assert not issubclass(RemoteMoved, StateSyncRefused)


def test_the_synced_tables_are_unique_keyed_and_disjoint_from_the_unsynced() -> None:
    names = [spec.name for spec in TABLES]
    assert len(names) == len(set(names))
    assert not set(names) & NOT_SYNCED
    assert all(spec.key for spec in TABLES)
    # The ledger is the one append-only table, and it is never resolved by a rule.
    assert [spec.name for spec in TABLES if spec.append_only] == ["event"]


# --- CanonicalJson --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (0, "0"),
        (-42, "-42"),
        (Decimal("1.10"), "1.10"),
        (Decimal("-0.000001"), "-0.000001"),
        (Decimal("1E+3"), "1E+3"),
        ("plain", '"plain"'),
        ('quote " and é', '"quote \\" and \\u00e9"'),
        ([], "[]"),
        ([1, "a", None, [True]], '[1,"a",null,[true]]'),
        ({}, "{}"),
        ({"b": 1, "a": {"d": [], "c": Decimal("2.5")}}, '{"a":{"c":2.5,"d":[]},"b":1}'),
    ],
)
def test_dumps_has_one_encoding_per_value(value: JsonValue, text: str) -> None:
    assert CANONICAL.dumps(value) == text


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_dumps_refuses_a_number_json_cannot_hold(value: Decimal) -> None:
    with pytest.raises(ValueError, match="has no JSON form"):
        CANONICAL.dumps(value)


@pytest.mark.parametrize("value", [1.5, (1, 2), {1, 2}, b"bytes"])
def test_dumps_refuses_what_is_not_a_json_value(value: object) -> None:
    with pytest.raises(TypeError, match="is not a JSON value"):
        CANONICAL.dumps(value)  # type: ignore[arg-type]


def test_loads_keeps_every_fraction_an_exact_decimal() -> None:
    loaded = CANONICAL.loads(b'{"cost":0.1,"big":1e2,"n":3,"s":"x","z":null}')
    assert loaded == {"cost": Decimal("0.1"), "big": Decimal("1e2"), "n": 3, "s": "x", "z": None}
    assert isinstance(loaded, dict)
    assert type(loaded["cost"]) is Decimal
    assert type(loaded["n"]) is int
    # The round trip through text is the identity on the exact value.
    assert CANONICAL.dumps(CANONICAL.loads("0.30")) == "0.30"


# --- TableSpec ------------------------------------------------------------------------------


def test_a_table_needs_a_key() -> None:
    with pytest.raises(ValueError, match="needs a key"):
        TableSpec("t", ())


def test_the_newest_rule_needs_a_timestamp_column() -> None:
    with pytest.raises(ValueError, match="needs newest_by"):
        TableSpec("t", ("id",), ConflictRule.NEWEST)


@pytest.mark.parametrize("rule", [ConflictRule.MINE, ConflictRule.THEIRS, ConflictRule.NEWEST])
def test_an_append_only_table_takes_only_refuse(rule: ConflictRule) -> None:
    with pytest.raises(ValueError, match="append-only"):
        TableSpec("t", ("id",), rule, "at", append_only=True)


def test_with_rule_keeps_everything_but_the_rule() -> None:
    spec = TableSpec(
        "job",
        ("id",),
        ConflictRule.NEWEST,
        "updated_at",
        deferred=("parent",),
        sequences=(("bump_seq", "job_bump_seq"),),
    )
    mine = spec.with_rule(ConflictRule.MINE)
    assert mine.rule is ConflictRule.MINE
    assert (mine.name, mine.key, mine.newest_by) == ("job", ("id",), "updated_at")
    assert (mine.append_only, mine.deferred, mine.sequences) == (
        False,
        ("parent",),
        (("bump_seq", "job_bump_seq"),),
    )
    assert spec.rule is ConflictRule.NEWEST  # the original is untouched


def test_with_rule_refuses_a_rule_its_table_cannot_take() -> None:
    with pytest.raises(ValueError, match="needs newest_by"):
        TableSpec("t", ("id",)).with_rule(ConflictRule.NEWEST)
    with pytest.raises(ValueError, match="append-only"):
        TableSpec("t", ("id",), append_only=True).with_rule(ConflictRule.MINE)


# --- Snapshot -------------------------------------------------------------------------------


def test_a_table_with_no_rows_is_the_same_state_as_a_table_not_named() -> None:
    kept: dict[str, Row] = {"[1]": row(1, "a")}
    snapshot = Snapshot(SCHEMA, {"empty": {}, "plain": kept})
    assert dict(snapshot.tables) == {"plain": kept}
    assert snapshot == Snapshot(SCHEMA, {"plain": kept})
    assert snapshot.rows("empty") == {}
    assert snapshot.rows("absent") == {}
    assert Snapshot(SCHEMA).tables == {}


def test_row_count_counts_every_row_of_every_table() -> None:
    assert Snapshot(SCHEMA).row_count == 0
    snapshot = snap(plain=[row(1, "a"), row(2, "b")], ledger=[event(1, "x")])
    assert snapshot.row_count == 3


# --- SnapshotCodec --------------------------------------------------------------------------


def test_the_codec_defaults_to_every_synced_table() -> None:
    assert SnapshotCodec().specs == TABLES
    assert CODEC.specs == SPECS


def test_a_row_is_keyed_by_the_canonical_encoding_of_its_key_columns() -> None:
    ledger = SPECS[1]
    assert CODEC.key(ledger, event(7, "x")) == '["p",7]'
    with pytest.raises(SnapshotUnreadable, match="a ledger row has no project, seq"):
        CODEC.key(ledger, {"kind": "x"})


def test_build_keys_every_row_and_drops_empty_tables() -> None:
    snapshot = CODEC.build(SCHEMA, {"plain": [row(2, "b"), row(1, "a")], "ours": []})
    assert snapshot.schema == SCHEMA
    assert set(snapshot.tables) == {"plain"}
    assert dict(snapshot.rows("plain")) == {"[1]": row(1, "a"), "[2]": row(2, "b")}


def test_build_takes_any_iterable_of_migrations() -> None:
    assert CODEC.build(iter(["0001"]), {}).schema == ("0001",)


def test_build_refuses_a_table_it_does_not_sync() -> None:
    with pytest.raises(SnapshotUnreadable, match="does not sync: alpha, zeta"):
        CODEC.build(SCHEMA, {"zeta": [], "plain": [], "alpha": []})


def test_build_refuses_two_rows_with_one_key() -> None:
    with pytest.raises(SnapshotUnreadable, match=r"two plain rows share the key \[1\]"):
        CODEC.build(SCHEMA, {"plain": [row(1, "a"), row(1, "b")]})


def test_two_equal_snapshots_are_equal_bytes_whatever_order_they_were_read_in() -> None:
    one = CODEC.build(SCHEMA, {"plain": [row(1, "a"), row(2, "b")], "ours": [row(9, "z")]})
    other = CODEC.build(
        SCHEMA,
        {
            "ours": [{"updated_at": None, "value": "z", "id": 9}],
            "plain": [row(2, "b"), row(1, "a")],
        },
    )
    assert CODEC.encode(one) == CODEC.encode(other)
    assert CODEC.digest(one) == CODEC.digest(other)
    assert CODEC.digest(one) == hashlib.sha256(CODEC.encode(one)).hexdigest()
    assert CODEC.digest(one) != CODEC.digest(snap(plain=[row(1, "a")]))


def test_the_document_lists_tables_parents_first_and_rows_by_key() -> None:
    snapshot = snap(plain=[row(2, "b"), row(1, "a")], dated=[row(5, "d", "2026-01-01")])
    encoded = CODEC.encode(snapshot)
    assert encoded.startswith(b'{"format":"vibey-state/1","schema":["0001_initial","0002_more"]')
    document = CANONICAL.loads(encoded)
    assert isinstance(document, dict)
    tables = document["tables"]
    assert isinstance(tables, dict)
    assert list(tables) == ["dated", "plain"]  # canonical: sorted keys
    assert tables["plain"] == [row(1, "a"), row(2, "b")]
    assert "ours" not in tables  # a table with no rows is not written


def test_encode_then_decode_is_the_identity_and_keeps_numbers_exact() -> None:
    snapshot = snap(
        plain=[
            {"id": 1, "cost": Decimal("0.10"), "payload": {"n": [1, Decimal("2.50")], "ok": True}},
            {"id": 2, "cost": None, "payload": {"text": 'é " \\ ✓'}, "flag": False},
        ],
        ledger=[event(1, "created"), event(2, "moved")],
    )
    decoded = CODEC.decode(CODEC.encode(snapshot))
    assert decoded == snapshot
    assert CODEC.encode(decoded) == CODEC.encode(snapshot)
    cost = decoded.rows("plain")["[1]"]["cost"]
    assert isinstance(cost, Decimal)
    assert str(cost) == "0.10"


def test_an_empty_snapshot_round_trips() -> None:
    empty = Snapshot(())
    assert CODEC.encode(empty) == b'{"format":"vibey-state/1","schema":[],"tables":{}}'
    assert CODEC.decode(CODEC.encode(empty)) == empty


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"not json", "is not JSON"),
        (b"\xff\xfe", "is not JSON"),
        (b"[]", f"not a {FORMAT} snapshot"),
        (b'"vibey-state/1"', f"not a {FORMAT} snapshot"),
        (b'{"format":"vibey-state/2","schema":[],"tables":{}}', f"not a {FORMAT} snapshot"),
        (b'{"schema":[],"tables":{}}', f"not a {FORMAT} snapshot"),
        (b'{"format":"vibey-state/1","tables":{}}', "schema is not a list"),
        (b'{"format":"vibey-state/1","schema":"0001","tables":{}}', "schema is not a list"),
        (b'{"format":"vibey-state/1","schema":["0001",2],"tables":{}}', "schema is not a list"),
        (b'{"format":"vibey-state/1","schema":[]}', "tables are not an object"),
        (b'{"format":"vibey-state/1","schema":[],"tables":[]}', "tables are not an object"),
        (b'{"format":"vibey-state/1","schema":[],"tables":{"plain":{}}}', "plain rows are not"),
        (b'{"format":"vibey-state/1","schema":[],"tables":{"plain":[1]}}', "plain rows are not"),
        (b'{"format":"vibey-state/1","schema":[],"tables":{"other":[]}}', "does not sync: other"),
        (b'{"format":"vibey-state/1","schema":[],"tables":{"plain":[{"v":1}]}}', "has no id"),
    ],
)
def test_decode_refuses_what_is_not_a_snapshot(data: bytes, message: str) -> None:
    with pytest.raises(SnapshotUnreadable, match=message):
        CODEC.decode(data)


@pytest.mark.parametrize("base", [None, "a" * 40])
def test_an_export_round_trips_with_its_remote_and_base(base: str | None) -> None:
    exported = Exported(snap(plain=[row(1, "a")]), "origin#vibey-state", base)
    data = CODEC.encode_export(exported)
    assert data.startswith(b'{"base":')
    assert f'"format":"{EXPORT_FORMAT}"'.encode() in data
    assert CODEC.decode_export(data) == exported


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"{", "the export is not JSON"),
        (b"[]", f"not a {EXPORT_FORMAT} file"),
        (b'{"format":"vibey-state/1"}', f"not a {EXPORT_FORMAT} file"),
        (b'{"format":"vibey-state-export/1","base":null}', "which remote it came from"),
        (b'{"format":"vibey-state-export/1","remote":7,"base":null}', "which remote"),
        (b'{"format":"vibey-state-export/1","remote":"r","base":7}', "which remote"),
        (b'{"format":"vibey-state-export/1","remote":"r","base":null}', "not a vibey-state/1"),
        (
            b'{"format":"vibey-state-export/1","remote":"r","base":null,"state":{"format":"x"}}',
            "not a vibey-state/1",
        ),
    ],
)
def test_decode_export_refuses_what_is_not_an_export(data: bytes, message: str) -> None:
    with pytest.raises(SnapshotUnreadable, match=message):
        CODEC.decode_export(data)


# --- StateMerger ----------------------------------------------------------------------------

MERGER = StateMerger(SPECS)


def merge_one(
    table: str, b: Row | None, m: Row | None, t: Row | None
) -> tuple[Row | None, tuple[str, ...]]:
    """Merge one row of one table; the merged row (None: absent) and every conflict reason."""

    def one(r: Row | None) -> Snapshot:
        return snap(**{table: [r] if r is not None else []})

    outcome = MERGER.merge(one(b), one(m), one(t))
    rows = list(outcome.merged.rows(table).values())
    assert len(rows) <= 1
    assert all(c.table == table for c in outcome.conflicts)
    return (rows[0] if rows else None), tuple(c.reason for c in outcome.conflicts)


A, B, C = row(1, "a"), row(1, "b"), row(1, "c")


@pytest.mark.parametrize(
    ("b", "m", "t", "expected"),
    [
        pytest.param(A, A, A, A, id="unchanged"),
        pytest.param(A, B, A, B, id="changed-here"),
        pytest.param(A, A, B, B, id="changed-there"),
        pytest.param(A, B, B, B, id="same-change-at-both"),
        pytest.param(None, A, None, A, id="added-here"),
        pytest.param(None, None, A, A, id="added-there"),
        pytest.param(None, A, A, A, id="same-row-added-at-both"),
        pytest.param(A, None, A, None, id="deleted-here"),
        pytest.param(A, A, None, None, id="deleted-there"),
        pytest.param(A, None, None, None, id="deleted-at-both"),
    ],
)
@pytest.mark.parametrize("table", ["plain", "ours", "yours", "dated"])
def test_a_row_only_one_end_changed_takes_that_change_under_every_rule(
    table: str, b: Row | None, m: Row | None, t: Row | None, expected: Row | None
) -> None:
    assert merge_one(table, b, m, t) == (expected, ())


def test_refuse_names_a_row_changed_differently_and_keeps_mine() -> None:
    assert merge_one("plain", A, B, C) == (B, ("changed differently at both ends",))
    assert merge_one("plain", None, B, C) == (B, ("changed differently at both ends",))


@pytest.mark.parametrize(("m", "t"), [(None, B), (B, None)])
def test_refuse_names_a_row_deleted_at_one_end_and_changed_at_the_other(
    m: Row | None, t: Row | None
) -> None:
    assert merge_one("plain", A, m, t) == (m, ("deleted at one end and changed at the other",))


def test_mine_and_theirs_settle_a_row_both_ends_changed() -> None:
    assert merge_one("ours", A, B, C) == (B, ())
    assert merge_one("yours", A, B, C) == (C, ())
    # Including a delete against a change: the rule's end wins outright.
    assert merge_one("ours", A, None, C) == (None, ())
    assert merge_one("yours", A, B, None) == (None, ())


@pytest.mark.parametrize(
    ("mine_at", "theirs_at", "winner"),
    [
        ("2026-10-06T10:00:01+00:00", "2026-10-06T10:00:00+00:00", "mine"),
        ("2026-10-06T10:00:00+00:00", "2026-10-06T10:00:01+00:00", "theirs"),
        ("2026-10-06T10:00:00", "2026-10-05T23:59:59", "mine"),
        # A missing time is the oldest.
        (None, "2026-10-06T10:00:00+00:00", "theirs"),
        ("2026-10-06T10:00:00+00:00", None, "mine"),
    ],
)
def test_newest_takes_the_row_with_the_later_timestamp(
    mine_at: str | None, theirs_at: str | None, winner: str
) -> None:
    mine, theirs = row(1, "mine", mine_at), row(1, "theirs", theirs_at)
    base = row(1, "base", "2026-01-01T00:00:00+00:00")
    assert merge_one("dated", base, mine, theirs) == (mine if winner == "mine" else theirs, ())


@pytest.mark.parametrize(
    ("mine_at", "theirs_at"),
    [
        # The same text.
        ("2026-10-06T10:00:00+00:00", "2026-10-06T10:00:00+00:00"),
        (None, None),
        # The same instant written two ways.
        ("2026-10-06T10:00:00+00:00", "2026-10-06T12:00:00+02:00"),
        # Not a time at all: nothing says which is newer.
        ("yesterday", "today"),
        ("2026-10-06T10:00:00+00:00", "soon"),
        # A time without its offset is not comparable with one that has it.
        ("2026-10-06T10:00:00", "2026-10-06T11:00:00+00:00"),
        ("2026-10-06T11:00:00+00:00", "2026-10-06T10:00:00"),
    ],
)
def test_newest_refuses_when_neither_row_is_newer(
    mine_at: str | None, theirs_at: str | None
) -> None:
    mine, theirs = row(1, "mine", mine_at), row(1, "theirs", theirs_at)
    assert merge_one("dated", row(1, "base"), mine, theirs) == (
        mine,
        ("changed at both ends with the same updated_at",),
    )


def test_newest_cannot_date_a_deleted_row() -> None:
    changed = row(1, "b", "2026-10-06T10:00:00+00:00")
    reason = ("deleted at one end and changed at the other",)
    assert merge_one("dated", A, None, changed) == (None, reason)
    assert merge_one("dated", A, changed, None) == (changed, reason)


def test_newest_compares_a_timestamp_the_row_does_not_carry_as_missing() -> None:
    mine: Row = {"id": 1, "value": "mine"}
    theirs = row(1, "theirs", "2026-10-06T10:00:00+00:00")
    assert merge_one("dated", A, mine, theirs) == (theirs, ())


E1, E1_OTHER = event(1, "created"), event(1, "forged")


@pytest.mark.parametrize(
    ("b", "m", "t", "expected"),
    [
        pytest.param(None, E1, None, E1, id="appended-here"),
        pytest.param(None, None, E1, E1, id="appended-there"),
        pytest.param(None, E1, E1, E1, id="appended-at-both"),
        pytest.param(E1, E1, E1, E1, id="unchanged"),
    ],
)
def test_a_ledger_row_is_the_same_row_at_every_end_it_is_at(
    b: Row | None, m: Row | None, t: Row | None, expected: Row
) -> None:
    assert merge_one("ledger", b, m, t) == (expected, ())


@pytest.mark.parametrize(
    ("m", "t"),
    [
        pytest.param(E1_OTHER, E1, id="changed-here"),
        pytest.param(E1, E1_OTHER, id="changed-there"),
        pytest.param(None, E1, id="removed-here"),
        pytest.param(E1, None, id="removed-there"),
        pytest.param(E1_OTHER, E1_OTHER, id="changed-identically-at-both"),
    ],
)
def test_a_ledger_row_is_never_changed_or_removed(m: Row | None, t: Row | None) -> None:
    assert merge_one("ledger", E1, m, t) == (
        m,
        ("a ledger row was changed or removed: the ledger is append-only",),
    )


def test_two_ends_that_appended_different_events_at_one_seq_have_diverged() -> None:
    merged, reasons = merge_one("ledger", None, E1, E1_OTHER)
    assert merged == E1
    assert len(reasons) == 1
    assert reasons[0].startswith("the ledger diverged")


def test_ledger_rows_appended_at_different_seqs_at_each_end_all_merge() -> None:
    base = snap(ledger=[event(1, "a")])
    mine = snap(ledger=[event(1, "a"), event(2, "here")])
    theirs = snap(ledger=[event(1, "a"), event(3, "there")])
    outcome = MERGER.merge(base, mine, theirs)
    assert outcome.conflicts == ()
    assert outcome.merged == snap(ledger=[event(1, "a"), event(2, "here"), event(3, "there")])


def test_a_merge_names_every_conflict_in_table_then_key_order() -> None:
    base = snap(plain=[row(2, "a"), row(1, "a")], ledger=[event(1, "a")])
    mine = snap(plain=[row(2, "m"), row(1, "m")], ledger=[event(1, "b")])
    theirs = snap(plain=[row(2, "t"), row(1, "t")], ledger=[event(1, "a")])
    outcome = MERGER.merge(base, mine, theirs)
    assert [(c.table, c.key) for c in outcome.conflicts] == [
        ("ledger", '["p",1]'),
        ("plain", "[1]"),
        ("plain", "[2]"),
    ]
    assert outcome.conflicts[1].describe() == "plain [1]: changed differently at both ends"


def test_with_no_base_and_no_other_end_the_merge_is_mine() -> None:
    mine = snap(plain=[row(1, "a")], ledger=[event(1, "x")])
    outcome = MERGER.merge(None, mine, None)
    assert outcome.merged == mine
    assert outcome.conflicts == ()


def test_with_no_base_two_ends_merge_as_a_first_sync() -> None:
    mine = snap(plain=[row(1, "a")])
    theirs = snap(plain=[row(2, "b")])
    assert MERGER.merge(None, mine, theirs).merged == snap(plain=[row(1, "a"), row(2, "b")])


def test_a_table_every_row_of_which_was_deleted_is_gone_from_the_merge() -> None:
    base = snap(plain=[row(1, "a")], ours=[row(1, "x")])
    mine = snap(ours=[row(1, "x")])
    outcome = MERGER.merge(base, mine, base)
    assert outcome.conflicts == ()
    assert set(outcome.merged.tables) == {"ours"}


def test_the_merge_is_idempotent() -> None:
    base = snap(plain=[row(1, "a")])
    mine = snap(plain=[row(1, "a"), row(2, "here")])
    theirs = snap(plain=[row(3, "there")])
    merged = MERGER.merge(base, mine, theirs).merged
    again = MERGER.merge(merged, merged, merged)
    assert again.merged == merged
    assert again.conflicts == ()


def test_the_merge_keeps_mine_schema() -> None:
    mine = snap(plain=[row(1, "a")])
    assert MERGER.merge(None, mine, snap()).merged.schema == SCHEMA


@pytest.mark.parametrize(
    ("mine_schema", "theirs_schema", "here", "there"),
    [
        (("0001",), ("0001", "0002"), "0001", "0002"),
        ((), ("0001",), "none", "0001"),
        (("0001",), (), "0001", "none"),
    ],
)
def test_two_ends_on_different_migrations_are_refused(
    mine_schema: tuple[str, ...], theirs_schema: tuple[str, ...], here: str, there: str
) -> None:
    with pytest.raises(SchemaMismatch) as raised:
        MERGER.merge(None, Snapshot(mine_schema), Snapshot(theirs_schema))
    message = str(raised.value)
    assert f"here: {here}, there: {there}" in message
    assert "vibey migrate" in message


def test_the_default_merger_covers_every_synced_table() -> None:
    codec = SnapshotCodec()
    project = {"id": "p1", "name": "x", "updated_at": "2026-10-06T10:00:00+00:00"}
    newer = {**project, "name": "y", "updated_at": "2026-10-06T11:00:00+00:00"}
    base = codec.build(SCHEMA, {"project": [project]})
    mine = codec.build(SCHEMA, {"project": [{**project, "name": "z"}]})
    theirs = codec.build(SCHEMA, {"project": [newer]})
    outcome = StateMerger().merge(base, mine, theirs)
    assert outcome.conflicts == ()
    assert outcome.merged.rows("project") == {'["p1"]': newer}


# --- SnapshotDiffer -------------------------------------------------------------------------


def test_the_diff_of_a_snapshot_with_itself_is_empty() -> None:
    snapshot = snap(plain=[row(1, "a")])
    diff = SnapshotDiffer(SPECS).diff(snapshot, snapshot)
    assert diff.empty
    assert diff.count() == 0
    assert SnapshotDiff().empty


def test_the_diff_names_every_added_changed_and_removed_row_parents_first() -> None:
    before = snap(plain=[row(1, "a"), row(2, "b"), row(3, "c")], ours=[row(1, "x")])
    after = snap(plain=[row(1, "a"), row(2, "B"), row(4, "d")], dated=[row(1, "new")])
    diff = SnapshotDiffer(SPECS).diff(before, after)
    assert not diff.empty
    assert diff.count() == 5
    assert diff.changes == (
        RowChange("dated", "[1]", None, row(1, "new")),
        RowChange("plain", "[2]", row(2, "b"), row(2, "B")),
        RowChange("plain", "[3]", row(3, "c"), None),
        RowChange("plain", "[4]", None, row(4, "d")),
        RowChange("ours", "[1]", row(1, "x"), None),
    )


def test_the_differ_ignores_tables_it_does_not_know() -> None:
    only_plain = SnapshotDiffer((SPECS[2],))
    assert only_plain.diff(snap(), snap(ours=[row(1, "x")])).empty
    assert SnapshotDiffer().diff(snap(), snap(plain=[row(1, "x")])).empty


# --- SyncReport -----------------------------------------------------------------------------

COMMIT = "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.parametrize(
    ("report", "text"),
    [
        (
            SyncReport(SyncState.IN_SYNC, "origin", commit=COMMIT, rows=3),
            "origin: in sync at 0123456789ab, 3 row(s)",
        ),
        (SyncReport(SyncState.IN_SYNC, "origin"), "origin: in sync, 0 row(s)"),
        (
            SyncReport(SyncState.SYNCED, "origin", pulled=2, pushed=True, commit=COMMIT, rows=5),
            "origin: synced at 0123456789ab: 2 row change(s) pulled, pushed; 5 row(s)",
        ),
        (
            SyncReport(SyncState.SYNCED, "origin", pulled=1, to_push=True, commit=COMMIT, rows=4),
            "origin: synced at 0123456789ab: 1 row change(s) pulled, changes here to push; "
            "4 row(s)",
        ),
        (
            SyncReport(SyncState.SYNCED, "origin", pulled=1, rows=1),
            "origin: synced: 1 row change(s) pulled, nothing to push; 1 row(s)",
        ),
        (
            SyncReport(SyncState.PENDING, "origin", pulled=2, to_push=True, commit=COMMIT, rows=5),
            "origin: 2 row change(s) to pull, changes here to push; 5 row(s)",
        ),
        (
            SyncReport(SyncState.PENDING, "origin", pulled=1, rows=2),
            "origin: 1 row change(s) to pull, nothing to push; 2 row(s)",
        ),
    ],
)
def test_a_report_says_what_was_done_or_is_to_do(report: SyncReport, text: str) -> None:
    assert report.describe() == text


def test_a_conflict_report_names_every_conflict_and_that_nothing_changed() -> None:
    report = SyncReport(
        SyncState.CONFLICT,
        "origin",
        commit=COMMIT,
        conflicts=(
            Conflict("plain", "[1]", "changed differently at both ends"),
            Conflict("ledger", '["p",2]', "the ledger diverged"),
        ),
    )
    assert report.describe() == (
        "origin: 2 conflict(s); nothing was changed at either end:\n"
        "  plain [1]: changed differently at both ends\n"
        '  ledger ["p",2]: the ledger diverged'
    )


# --- ConflictRules --------------------------------------------------------------------------


def test_no_overrides_leaves_every_table_as_declared() -> None:
    assert ConflictRules().apply("") == TABLES
    assert ConflictRules().apply(" , ,", SPECS) == SPECS


def test_overrides_change_only_the_tables_they_name() -> None:
    specs = ConflictRules().apply(" plain = theirs ,, ours=refuse,", SPECS)
    rules = {spec.name: spec.rule for spec in specs}
    assert rules == {
        "dated": ConflictRule.NEWEST,
        "ledger": ConflictRule.REFUSE,
        "plain": ConflictRule.THEIRS,
        "ours": ConflictRule.REFUSE,
        "yours": ConflictRule.THEIRS,
    }
    assert [spec.name for spec in specs] == [spec.name for spec in SPECS]


def test_the_last_override_of_a_table_wins() -> None:
    specs = ConflictRules().apply("handoff=mine,handoff=theirs")
    assert {s.name: s.rule for s in specs}["handoff"] is ConflictRule.THEIRS


@pytest.mark.parametrize("text", ["plain", "plain:mine", "=mine", "nope=mine", "event_seq=mine"])
def test_an_override_that_is_not_table_equals_rule_for_a_synced_table_is_refused(
    text: str,
) -> None:
    with pytest.raises(ValueError, match="is not table=rule for a synced table"):
        ConflictRules().apply(text, SPECS if text != "event_seq=mine" else TABLES)


@pytest.mark.parametrize("rule", ["", "MINE", "oldest"])
def test_an_unknown_rule_is_refused_naming_the_rules(rule: str) -> None:
    with pytest.raises(ValueError, match="is not a rule: one of newest, mine, theirs, refuse"):
        ConflictRules().apply(f"plain={rule}", SPECS)


def test_an_override_its_table_cannot_take_is_refused() -> None:
    with pytest.raises(ValueError, match="needs newest_by"):
        ConflictRules().apply("handoff=newest")
    with pytest.raises(ValueError, match="append-only"):
        ConflictRules().apply("event=mine")
