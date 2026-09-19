# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Exporting a shard and planning its site: counts that add up, a chain head that is the
ledger's, and a shard that is checked before anything is published from it."""

import asyncio
import dataclasses
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from uuid import UUID, uuid4

import pytest

from vibey.application.interfaces import (
    LedgerReader,
    LedgerShardInterface,
    LedgerShardStore,
    LedgerSitePlanInterface,
    LedgerSiteWriter,
    SearchTokenizerInterface,
    ShardHeaderInterface,
)
from vibey.application.ledger_publication import (
    SEARCH_TOKENIZER,
    SHARD_FORMAT,
    SITE_FORMAT,
    UNTIERED,
    InvalidLedgerShard,
    LedgerExporter,
    LedgerShard,
    LedgerSiteBuilder,
    SearchTokenizer,
    ShardHolding,
)
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event, digest_range
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.domain.phase import Phase
from vibey.domain.publication_policy import (
    DEFAULT_POLICY,
    DEFAULT_RULES,
    TrimCounts,
    WithheldReason,
)

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000004")
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _event(seq: int, **overrides: object) -> LedgerEvent:
    payload = overrides.pop("payload", {"decision_id": f"d{seq}", "title": f"decision {seq}"})
    fields: dict[str, object] = {
        "event_id": UUID(int=seq),
        "project_id": PROJECT,
        "cycle": 1,
        "phase": Phase.DESIGN,
        "seq": seq,
        "kind": EventKind.DECISION_RECORDED,
        "engine_id": None,
        "job_id": None,
        "causation_id": None,
        "correlation_id": PROJECT,
        "provenance": Provenance.TRUSTED,
        "produced_at": T0 + timedelta(seconds=seq),
        "payload": payload,
        "digest": digest_event(payload),  # type: ignore[arg-type]
    }
    fields.update(overrides)
    return LedgerEvent(**fields)  # type: ignore[arg-type]


def _ledger() -> tuple[LedgerEvent, ...]:
    return (
        _event(1, kind=EventKind.PHASE_TRANSITIONED, payload={"from": "intake", "to": "design"}),
        _event(2, kind=EventKind.TURN_COMPLETED, engine_id=EngineId.CLAUDELOOP),
        _event(3, payload={"title": "keep /Users/adam/x", "internal": "hidden"}),
        _event(4, provenance=Provenance.UNTRUSTED),
        _event(
            5,
            kind=EventKind.FINDING_RAISED,
            engine_id=EngineId.CODEXLOOP,
            produced_at=datetime(2026, 9, 18, 14, 0, 5, tzinfo=timezone(timedelta(hours=2))),
            payload={"finding_id": "f1", "text": "Flaky TEST in a b", "severity": "high"},
        ),
        _event(6, kind=EventKind.BUDGET_SPENT, payload={"dollars": 1.5}),
    )


class _Reader:
    def __init__(self, events: Sequence[LedgerEvent]) -> None:
        self._events = tuple(events)
        self.asked: list[UUID] = []

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        self.asked.append(project_id)
        return self._events


class _Store:
    def __init__(self, shard: LedgerShardInterface | None = None) -> None:
        self.shard = shard
        self.written: list[tuple[LedgerShardInterface, Path]] = []
        self.read_from: list[Path] = []

    def write(self, shard: LedgerShardInterface, path: Path) -> None:
        self.written.append((shard, path))

    def read(self, path: Path) -> LedgerShardInterface:
        self.read_from.append(path)
        assert self.shard is not None
        return self.shard


class _Writer:
    def __init__(self) -> None:
        self.written: list[tuple[LedgerSitePlanInterface, Path]] = []

    def write(self, plan: LedgerSitePlanInterface, directory: Path) -> None:
        self.written.append((plan, directory))


def _exporter(events: Sequence[LedgerEvent] = ()) -> LedgerExporter:
    return LedgerExporter(ledger=_Reader(events), store=_Store(), policy=DEFAULT_POLICY)


def _shard(events: Sequence[LedgerEvent] | None = None) -> LedgerShard:
    return _exporter().shard(PROJECT, "greeter", _ledger() if events is None else events)


def _builder(shard: LedgerShardInterface | None = None) -> LedgerSiteBuilder:
    return LedgerSiteBuilder(store=_Store(shard), writer=_Writer())


def _with_header(shard: LedgerShardInterface, **changes: object) -> LedgerShard:
    header = dataclasses.replace(shard.header, **changes)  # type: ignore[type-var]
    return LedgerShard(header=header, records=shard.records)


def test_the_fakes_satisfy_the_ports() -> None:
    assert isinstance(_Reader(()), LedgerReader)
    assert isinstance(_Store(), LedgerShardStore)
    assert isinstance(_Writer(), LedgerSiteWriter)
    assert isinstance(SEARCH_TOKENIZER, SearchTokenizerInterface)


# -- export ------------------------------------------------------------------------


def test_the_shard_publishes_what_the_policy_allows_and_counts_the_rest() -> None:
    shard = _shard()
    header = shard.header

    assert isinstance(header, ShardHeaderInterface)
    assert [record.seq for record in shard.records] == [1, 3, 5]
    assert shard.records[1].payload == {"title": "keep [path]"}
    assert header.format == SHARD_FORMAT
    assert (header.project_id, header.project_name) == (PROJECT, "greeter")
    assert header.holds is ShardHolding.FULL
    assert header.tier == UNTIERED
    assert (header.ledger_first_seq, header.ledger_last_seq, header.ledger_event_count) == (1, 6, 6)
    assert dict(header.withheld) == {
        WithheldReason.UNTRUSTED_PROVENANCE: 1,
        WithheldReason.ENGINE_CHATTER: 1,
        WithheldReason.KIND_NOT_ALLOWLISTED: 1,
    }
    assert header.events_withheld == 3
    assert header.published_count == 3
    assert header.trimmed == TrimCounts(fields=1, paths=1)
    assert dict(header.trims) == {UUID(int=3): TrimCounts(fields=1, paths=1)}
    assert header.published_digest_range == digest_range(shard.records)
    assert (header.policy_scheme, header.policy_fingerprint) == (
        DEFAULT_RULES.scheme,
        DEFAULT_RULES.fingerprint,
    )


def test_the_chain_head_is_the_ledgers_own_over_every_event_withheld_included() -> None:
    ledger = _ledger()
    header = _shard(tuple(reversed(ledger))).header
    verification = LEDGER_CHAIN.verify(PROJECT, ledger)

    assert header.chain_head == verification.head
    assert header.chain_scheme == LEDGER_CHAIN.scheme
    assert header.chain_findings == 0
    # Not a chain over the published records alone.
    assert header.chain_head != LEDGER_CHAIN.verify(PROJECT, _shard().records).head


def test_a_ledger_that_does_not_start_at_seq_one_is_a_window_and_unverified() -> None:
    header = _shard(_ledger()[2:]).header
    assert header.holds is ShardHolding.WINDOW
    assert header.ledger_first_seq == 3
    assert header.chain_findings == 1


def test_an_empty_ledger_is_a_full_shard_of_nothing_anchored_at_genesis() -> None:
    header = _shard(()).header
    assert header.holds is ShardHolding.FULL
    assert (header.ledger_first_seq, header.ledger_last_seq, header.ledger_event_count) == (
        None,
        None,
        0,
    )
    assert header.chain_head == LEDGER_CHAIN.genesis(PROJECT)
    assert header.published_count == 0


def test_export_reads_the_whole_ledger_and_hands_the_shard_to_the_store(tmp_path: Path) -> None:
    reader, store = _Reader(_ledger()), _Store()
    exporter = LedgerExporter(
        ledger=reader, store=store, policy=DEFAULT_POLICY, tier="archival", shard_format="x/v9"
    )
    out = tmp_path / "shard.jsonl"

    shard = asyncio.run(exporter.export(PROJECT, "greeter", out))

    assert reader.asked == [PROJECT]
    assert store.written == [(shard, out)]
    assert (shard.header.tier, shard.header.format) == ("archival", "x/v9")


# -- the site plan ------------------------------------------------------------------


def test_the_plan_lays_out_one_document_per_record_an_index_and_a_manifest() -> None:
    plan = _builder().plan(_shard())

    assert sorted(plan.documents) == [
        "index.json",
        "manifest.json",
        f"records/{UUID(int=1)}.json",
        f"records/{UUID(int=3)}.json",
        f"records/{UUID(int=5)}.json",
    ]


def test_a_record_document_carries_the_record_what_was_withheld_and_its_neighbours() -> None:
    shard = _shard()
    documents = _builder().plan(shard).documents
    first, middle, last = (documents[f"records/{UUID(int=n)}.json"] for n in (1, 3, 5))

    assert middle["format"] == SITE_FORMAT
    assert middle["project_id"] == str(PROJECT)
    assert middle["record"] == LEDGER_RECORDS.to_fields(shard.records[1])
    assert middle["withheld"] == {"fields": 1, "paths": 1, "emails": 0, "credentials": 0}
    assert middle["previous"] == {
        "event_id": str(UUID(int=1)),
        "seq": 1,
        "digest": shard.records[0].digest,
    }
    assert middle["next"] == {
        "event_id": str(UUID(int=5)),
        "seq": 5,
        "digest": shard.records[2].digest,
    }
    assert first["previous"] is None
    assert first["withheld"] == {"fields": 0, "paths": 0, "emails": 0, "credentials": 0}
    assert last["next"] is None


def test_the_index_has_every_search_dimension_per_record() -> None:
    index = _builder().plan(_shard()).documents["index.json"]
    entries = index["records"]

    assert index["format"] == SITE_FORMAT
    assert isinstance(entries, list)
    assert [entry["seq"] for entry in entries] == [1, 3, 5]
    finding = entries[2]
    assert finding == {
        "id": str(UUID(int=5)),
        "seq": 5,
        "kind": "FindingRaised",
        "phase": "design",
        "actor": "codexloop",
        "time": "2026-09-18T12:00:05+00:00",
        "digest": _shard().records[2].digest,
        "tokens": ["f1", "flaky", "high", "in", "test"],
    }
    assert entries[0]["actor"] == "vibey"


def test_the_manifest_says_what_the_shard_holds_and_everything_withheld() -> None:
    shard = _shard()
    manifest = _builder().plan(shard).documents["manifest.json"]

    assert manifest == {
        "format": SITE_FORMAT,
        "shard_format": SHARD_FORMAT,
        "project": {"project_id": str(PROJECT), "name": "greeter"},
        "holds": "full",
        "tier": UNTIERED,
        "seq_range": {"first": 1, "last": 6, "events": 6},
        "published": {"records": 3, "first_seq": 1, "last_seq": 5},
        "digest_range": digest_range(shard.records),
        "chain": {
            "scheme": LEDGER_CHAIN.scheme,
            "head": LEDGER_CHAIN.verify(PROJECT, _ledger()).head,
            "head_seq": 6,
            "verified": True,
            "findings": 0,
        },
        "policy": {"scheme": DEFAULT_RULES.scheme, "fingerprint": DEFAULT_RULES.fingerprint},
        "withheld": {
            "events": 3,
            "by_reason": {
                "untrusted_provenance": 1,
                "engine_chatter": 1,
                "kind_not_allowlisted": 1,
            },
            "fields": 1,
            "paths": 1,
            "emails": 0,
            "credentials": 0,
        },
        "statement": "3 events withheld by policy",
        "documents": {"index": "index.json", "records": "records/{event_id}.json"},
    }


def test_an_empty_shard_plans_an_empty_index_and_says_so() -> None:
    manifest = _builder().plan(_shard(())).documents["manifest.json"]
    assert manifest["published"] == {"records": 0, "first_seq": None, "last_seq": None}
    assert manifest["statement"] == "0 events withheld by policy"


def test_one_withheld_event_is_singular() -> None:
    manifest = _builder().plan(_shard(_ledger()[:2])).documents["manifest.json"]
    assert manifest["statement"] == "1 event withheld by policy"


def test_the_layout_and_vocabulary_are_configurable() -> None:
    builder = LedgerSiteBuilder(
        store=_Store(),
        writer=_Writer(),
        tokenizer=SearchTokenizer(min_length=1),
        self_actor="conductor",
        records_dir="r",
        index_name="i.json",
        manifest_name="m.json",
        site_format="site/v2",
    )
    documents = builder.plan(_shard()).documents

    assert sorted(documents)[:2] == ["i.json", "m.json"]
    index = documents["i.json"]
    assert index["format"] == "site/v2"
    assert index["records"][0]["actor"] == "conductor"  # type: ignore[index]
    assert "a" in index["records"][2]["tokens"]  # type: ignore[index]
    assert documents["m.json"]["documents"] == {"index": "i.json", "records": "r/{event_id}.json"}


def test_the_plan_is_deterministic() -> None:
    def rendered() -> str:
        plan = _builder().plan(_shard())
        return json.dumps(dict(plan.documents), sort_keys=True, default=str)

    assert rendered() == rendered()


def test_build_reads_the_shard_plans_it_and_hands_the_plan_to_the_writer(tmp_path: Path) -> None:
    shard = _shard()
    store, writer = _Store(shard), _Writer()
    builder = LedgerSiteBuilder(store=store, writer=writer)

    plan = builder.build(tmp_path / "in.jsonl", tmp_path / "site")

    assert store.read_from == [tmp_path / "in.jsonl"]
    assert writer.written == [(plan, tmp_path / "site")]
    assert plan.shard is shard


# -- a shard is checked before it is published ----------------------------------------


def _records(shard: LedgerShardInterface, *records: LedgerEvent) -> LedgerShard:
    return LedgerShard(header=shard.header, records=records)


def test_a_shard_of_another_format_is_refused() -> None:
    with pytest.raises(InvalidLedgerShard, match="unsupported shard format 'x/v9'"):
        _builder().plan(_with_header(_shard(), format="x/v9"))


def test_a_record_of_another_project_is_refused() -> None:
    shard = _shard()
    stranger = dataclasses.replace(shard.records[0], project_id=uuid4())
    with pytest.raises(InvalidLedgerShard, match="record seq 1 belongs to project"):
        _builder().plan(_records(shard, stranger, *shard.records[1:]))


def test_records_out_of_order_are_refused() -> None:
    shard = _shard()
    with pytest.raises(InvalidLedgerShard, match="record seq 1 follows seq 3"):
        _builder().plan(_records(shard, shard.records[1], shard.records[0]))


def test_a_record_outside_the_stated_range_is_refused() -> None:
    shard = _shard()
    with pytest.raises(InvalidLedgerShard, match=r"record seq 5 is outside .* \(1\.\.4\)"):
        _builder().plan(_with_header(shard, ledger_last_seq=4))
    with pytest.raises(InvalidLedgerShard, match=r"outside .* \(None\.\.None\)"):
        _builder().plan(_with_header(shard, ledger_first_seq=None, ledger_last_seq=None))


def test_a_repeated_event_id_is_refused() -> None:
    shard = _shard()
    twin = dataclasses.replace(shard.records[2], event_id=shard.records[0].event_id)
    with pytest.raises(InvalidLedgerShard, match="record seq 5 repeats event id"):
        _builder().plan(_records(shard, *shard.records[:2], twin))


def test_a_record_whose_payload_was_changed_after_export_is_refused() -> None:
    shard = _shard()
    edited = dataclasses.replace(shard.records[1], payload={"title": "edited"})
    with pytest.raises(InvalidLedgerShard, match="record seq 3: its digest is not"):
        _builder().plan(_records(shard, shard.records[0], edited, shard.records[2]))


def test_a_lost_record_is_refused_by_the_count() -> None:
    shard = _shard()
    with pytest.raises(
        InvalidLedgerShard, match="states 3 published record\\(s\\); the shard holds 2"
    ):
        _builder().plan(_records(shard, shard.records[0], shard.records[2]))


def test_counts_that_do_not_add_up_are_refused() -> None:
    with pytest.raises(InvalidLedgerShard, match="counts do not add up: 7 event"):
        _builder().plan(_with_header(_shard(), ledger_event_count=7))


def test_a_digest_range_that_does_not_match_is_refused() -> None:
    with pytest.raises(InvalidLedgerShard, match="digest_range is not the one the header states"):
        _builder().plan(_with_header(_shard(), published_digest_range="0" * 64))


def test_trims_that_do_not_add_up_to_the_total_are_refused() -> None:
    with pytest.raises(InvalidLedgerShard, match="per-record trims do not add up"):
        _builder().plan(_with_header(_shard(), trimmed=TrimCounts(fields=9)))


def test_trims_for_a_record_the_shard_does_not_hold_are_refused() -> None:
    shard = _shard()
    stray = uuid4()
    trims = MappingProxyType({**shard.header.trims, stray: TrimCounts(paths=1)})
    trimmed = shard.header.trimmed.plus(TrimCounts(paths=1))
    with pytest.raises(InvalidLedgerShard, match=f"does not hold: {stray}"):
        _builder().plan(_with_header(shard, trims=trims, trimmed=trimmed))


# -- the tokenizer -----------------------------------------------------------------------


def test_tokens_are_lower_cased_words_from_every_string_and_number_once_and_sorted() -> None:
    tokens = SearchTokenizer().tokens(
        {
            "title": "Use Postgres, not SQLite!",
            "n": 2026,
            "ratio": 0.75,
            "flag": True,
            "none": None,
            "nested": {"list": ["postgres", ("Tuple", "x")], "id": UUID(int=0xAB)},
        }
    )
    assert tokens == (
        "0000",
        "00000000",
        "0000000000ab",
        "2026",
        "75",
        "not",
        "postgres",
        "sqlite",
        "tuple",
        "use",
    )


def test_the_minimum_token_length_is_configurable() -> None:
    assert SearchTokenizer(min_length=1).tokens({"t": "a bb"}) == ("a", "bb")
    assert SearchTokenizer(min_length=3).tokens({"t": "a bb ccc"}) == ("ccc",)
