# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The shard file and the static site on disk: the same input always writes the same
bytes, nothing a payload says can become markup, and a file that is not a shard is
refused with the line and the field at fault."""

import asyncio
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from uuid import UUID

import pytest

from vibey.application.interfaces import LedgerShardStore, LedgerSiteWriter
from vibey.application.ledger_publication import (
    InvalidLedgerShard,
    LedgerExporter,
    LedgerShard,
    LedgerSiteBuilder,
    LedgerSitePlan,
)
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.phase import Phase
from vibey.domain.publication_policy import PublicationPolicy
from vibey.infrastructure.ledger.full_ledger_writer import LEDGER_LINES
from vibey.infrastructure.ledger.interfaces import HtmlSafeJsonInterface, ShardHeaderCodecInterface
from vibey.infrastructure.ledger.redact import CREDENTIAL_REDACTOR
from vibey.infrastructure.ledger.static_export import (
    DEFAULT_HEADER_KEY,
    HTML_SAFE_JSON,
    SHARD_HEADERS,
    HtmlSafeJson,
    JsonlShardStore,
    ShardHeaderCodec,
    StaticSiteWriter,
)

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000005")
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
SCRIPT = "<script>alert('pwned')</script> & </p>"
REPO = "/Users/operator/private/checkout"
POLICY = PublicationPolicy(redactor=CREDENTIAL_REDACTOR)


def _event(seq: int, **overrides: object) -> LedgerEvent:
    payload = overrides.pop("payload", {"decision_id": f"d{seq}", "title": f"decision {seq}"})
    fields: dict[str, object] = {
        "event_id": UUID(int=seq),
        "project_id": PROJECT,
        "cycle": 1,
        "phase": Phase.BUILD,
        "seq": seq,
        "kind": EventKind.DECISION_RECORDED,
        "engine_id": None,
        "job_id": None,
        "causation_id": None,
        "correlation_id": PROJECT,
        "provenance": Provenance.TRUSTED,
        "produced_at": T0 + timedelta(minutes=seq),
        "payload": payload,
        "digest": digest_event(payload),  # type: ignore[arg-type]
    }
    fields.update(overrides)
    return LedgerEvent(**fields)  # type: ignore[arg-type]


def _ledger() -> tuple[LedgerEvent, ...]:
    return (
        _event(1, payload={"title": SCRIPT, "repo_path": REPO}),
        _event(2, kind=EventKind.TOOL_INVOKED, engine_id=EngineId.CLAUDELOOP),
        _event(3, payload={"title": f"cd {REPO} && mail ops@example.com", "secret": "x"}),
        _event(4, payload={"title": "token sk-abcdefghijklmnopqrstuvwx leaked"}),
    )


class _Reader:
    def __init__(self, events: Sequence[LedgerEvent]) -> None:
        self._events = tuple(events)

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return self._events


def _shard(events: Sequence[LedgerEvent] | None = None) -> LedgerShard:
    exporter = LedgerExporter(ledger=_Reader(()), store=JsonlShardStore(), policy=POLICY)
    return exporter.shard(PROJECT, "greeter", _ledger() if events is None else events)


def _export(path: Path, events: Sequence[LedgerEvent] | None = None) -> None:
    exporter = LedgerExporter(
        ledger=_Reader(_ledger() if events is None else events),
        store=JsonlShardStore(),
        policy=POLICY,
    )
    asyncio.run(exporter.export(PROJECT, "greeter", path))


def _site(shard_path: Path, out: Path) -> LedgerSitePlan:
    return LedgerSiteBuilder(store=JsonlShardStore(), writer=StaticSiteWriter()).build(
        shard_path, out
    )


def _files(directory: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def test_the_adapters_satisfy_their_seams() -> None:
    assert isinstance(JsonlShardStore(), LedgerShardStore)
    assert isinstance(StaticSiteWriter(), LedgerSiteWriter)
    assert isinstance(SHARD_HEADERS, ShardHeaderCodecInterface)
    assert isinstance(HTML_SAFE_JSON, HtmlSafeJsonInterface)


# -- the shard file ------------------------------------------------------------------


def test_a_shard_is_a_header_line_then_one_record_line_each(tmp_path: Path) -> None:
    shard = _shard()
    path = tmp_path / "ledger" / "greeter.jsonl"

    JsonlShardStore().write(shard, path)
    text = path.read_text()
    lines = text.splitlines()

    assert text.endswith("\n")
    assert set(json.loads(lines[0])) == {DEFAULT_HEADER_KEY}
    assert lines[1:] == [LEDGER_LINES.encode(record) for record in shard.records]


def test_a_shard_reads_back_as_it_was_written(tmp_path: Path) -> None:
    shard = _shard()
    path = tmp_path / "shard.jsonl"
    store = JsonlShardStore()
    store.write(shard, path)

    read = store.read(path)

    assert read.records == shard.records
    assert SHARD_HEADERS.to_document(read.header) == SHARD_HEADERS.to_document(shard.header)
    assert read.header.trims == shard.header.trims


def test_an_empty_ledger_round_trips_with_no_seq_range(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    store = JsonlShardStore()
    store.write(_shard(()), path)

    header = store.read(path).header
    assert (header.ledger_first_seq, header.ledger_last_seq) == (None, None)
    assert len(path.read_text().splitlines()) == 1


def test_the_same_ledger_always_writes_the_same_bytes(tmp_path: Path) -> None:
    _export(tmp_path / "a.jsonl")
    _export(tmp_path / "b.jsonl", tuple(reversed(_ledger())))
    assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()


def test_blank_lines_are_not_records(tmp_path: Path) -> None:
    path = tmp_path / "shard.jsonl"
    JsonlShardStore().write(_shard(), path)
    path.write_text(path.read_text().replace("\n", "\n\n"))

    assert len(JsonlShardStore().read(path).records) == 3


def test_the_header_key_is_configurable(tmp_path: Path) -> None:
    store = JsonlShardStore(header_key="ledger-shard")
    path = tmp_path / "shard.jsonl"
    store.write(_shard(), path)

    assert set(json.loads(path.read_text().splitlines()[0])) == {"ledger-shard"}
    assert store.read(path).header.project_name == "greeter"
    with pytest.raises(InvalidLedgerShard, match='"shard"'):
        JsonlShardStore().read(path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "the file is empty"),
        (b"\xff\xfe not utf-8", "cannot read"),
        (b"{nope\n", "line 1: not JSON"),
        (b"[]\n", "line 1: a shard starts with its header"),
        (b'{"shard": {}, "extra": 1}\n', "line 1: a shard starts with its header"),
    ],
)
def test_a_file_that_is_not_a_shard_is_refused(
    tmp_path: Path, content: bytes, message: str
) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_bytes(content)
    with pytest.raises(InvalidLedgerShard, match=message):
        JsonlShardStore().read(path)


def test_a_missing_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InvalidLedgerShard, match="cannot read"):
        JsonlShardStore().read(tmp_path / "absent.jsonl")


def test_a_bad_record_line_is_refused_with_its_line_number(tmp_path: Path) -> None:
    path = tmp_path / "shard.jsonl"
    JsonlShardStore().write(_shard(), path)
    lines = path.read_text().splitlines()
    lines[2] = lines[2].replace('"seq":3', '"seq":"three"')
    path.write_text("\n".join(lines) + "\n")

    with pytest.raises(InvalidLedgerShard, match="line 3: 'seq' must be an integer"):
        JsonlShardStore().read(path)


# -- the header codec ------------------------------------------------------------------


def _document(**changes: object) -> dict[str, object]:
    document = ShardHeaderCodec().to_document(_shard().header)
    for dotted, value in changes.items():
        *parents, leaf = dotted.split("__")
        table = document
        for parent in parents:
            table = table[parent]  # type: ignore[assignment]
        if value is ...:
            del table[leaf]
        else:
            table[leaf] = value
    return document


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"ledger": []}, "shard.ledger must be a JSON object"),
        ({"format": ...}, "shard.format must be a string"),
        ({"project_id": "nope"}, "shard.project_id is not a UUID"),
        ({"holds": "some"}, "shard.holds is 'some'; it must be one of full, window"),
        ({"ledger__event_count": True}, "shard.ledger.event_count must be a whole number"),
        ({"ledger__first_seq": -1}, "shard.ledger.first_seq must be a whole number"),
        ({"chain__findings": "0"}, "shard.chain.findings must be a whole number"),
        ({"withheld__events": []}, "shard.withheld.events must be a JSON object"),
        (
            {"withheld__events__engine_chatter": ...},
            "must count exactly these reasons: engine_chatter, kind_not_allowlisted, "
            "untrusted_provenance; it has kind_not_allowlisted, untrusted_provenance",
        ),
        ({"withheld__events": {}}, "; it has none"),
        ({"withheld__paths": ...}, "shard.withheld.paths must be a whole number"),
        ({"trims": {"not-a-uuid": {}}}, "shard.trims key 'not-a-uuid' is not a UUID"),
        ({"trims": {str(UUID(int=3)): 5}}, "must be a JSON object"),
    ],
)
def test_a_header_that_is_not_one_is_refused_by_field(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(InvalidLedgerShard, match=message):
        ShardHeaderCodec().from_document(_document(**changes))


def test_a_header_that_is_not_an_object_is_refused() -> None:
    with pytest.raises(InvalidLedgerShard, match="^shard must be a JSON object$"):
        ShardHeaderCodec().from_document("header")


# -- the site ------------------------------------------------------------------------------


def test_the_site_is_the_documents_of_the_plan(tmp_path: Path) -> None:
    _export(tmp_path / "shard.jsonl")
    plan = _site(tmp_path / "shard.jsonl", tmp_path / "site")

    written = _files(tmp_path / "site")
    assert sorted(written) == sorted(plan.documents)
    for relative, document in plan.documents.items():
        assert json.loads(written[relative]) == json.loads(json.dumps(document))


def test_the_manifest_chain_head_is_the_ledgers(tmp_path: Path) -> None:
    _export(tmp_path / "shard.jsonl")
    _site(tmp_path / "shard.jsonl", tmp_path / "site")
    manifest = json.loads((tmp_path / "site" / "manifest.json").read_text())

    assert manifest["chain"]["head"] == LEDGER_CHAIN.verify(PROJECT, _ledger()).head
    assert manifest["chain"]["head_seq"] == 4
    assert manifest["withheld"] == {
        "events": 1,
        "by_reason": {"engine_chatter": 1, "kind_not_allowlisted": 0, "untrusted_provenance": 0},
        "fields": 2,
        "paths": 1,
        "emails": 1,
        "credentials": 1,
    }


def test_site_output_is_deterministic(tmp_path: Path) -> None:
    _export(tmp_path / "shard.jsonl")
    _site(tmp_path / "shard.jsonl", tmp_path / "one")
    _site(tmp_path / "shard.jsonl", tmp_path / "two")
    first = _files(tmp_path / "one")

    assert first == _files(tmp_path / "two")
    _site(tmp_path / "shard.jsonl", tmp_path / "one")
    assert _files(tmp_path / "one") == first


def test_script_shaped_payloads_survive_only_as_data(tmp_path: Path) -> None:
    _export(tmp_path / "shard.jsonl")
    _site(tmp_path / "shard.jsonl", tmp_path / "site")
    record = tmp_path / "site" / "records" / f"{UUID(int=1)}.json"

    for text in (path.read_text() for path in (tmp_path / "site").rglob("*.json")):
        assert "<" not in text and ">" not in text and "&" not in text
    assert json.loads(record.read_text())["record"]["payload"]["title"] == SCRIPT


def test_nothing_withheld_reaches_the_shard_or_the_site(tmp_path: Path) -> None:
    _export(tmp_path / "shard.jsonl")
    _site(tmp_path / "shard.jsonl", tmp_path / "site")
    published = (tmp_path / "shard.jsonl").read_text() + "".join(
        path.read_text() for path in (tmp_path / "site").rglob("*.json")
    )

    for leaked in ("/Users/operator", "ops@example.com", "sk-abcdefghij", "repo_path", "secret"):
        assert leaked not in published


def test_stale_records_are_removed_and_nothing_else_is(tmp_path: Path) -> None:
    site = tmp_path / "site"
    (site / "records").mkdir(parents=True)
    (site / "records" / "gone.json").write_text("{}")
    (site / "records" / "notes.txt").write_text("mine")
    (site / "index.html").write_text("mine too")
    (site / "other.json").write_text("{}")
    _export(tmp_path / "shard.jsonl")

    _site(tmp_path / "shard.jsonl", site)

    assert not (site / "records" / "gone.json").exists()
    assert (site / "records" / "notes.txt").read_text() == "mine"
    assert (site / "index.html").read_text() == "mine too"
    assert (site / "other.json").exists()


@pytest.mark.parametrize(
    "relative", ["/etc/passwd.json", "../escape.json", "records/../../x.json", ""]
)
def test_a_document_path_outside_the_site_is_refused(tmp_path: Path, relative: str) -> None:
    plan = LedgerSitePlan(shard=_shard(), documents=MappingProxyType({relative: {}}))
    with pytest.raises(InvalidLedgerShard, match="refusing to write outside the site"):
        StaticSiteWriter().write(plan, tmp_path / "site")


# -- the encoder -------------------------------------------------------------------------------


def test_served_json_is_sorted_ascii_and_inert_inside_html() -> None:
    document = {"z": "</script><b>&amp;", "a": "café  "}
    text = HtmlSafeJson().dumps(document)

    assert text.endswith("}\n")
    assert text.index('"a"') < text.index('"z"')
    assert text.isascii()
    assert not {"<", ">", "&"} & set(text)
    assert json.loads(text) == document


def test_the_encoder_refuses_numbers_json_cannot_carry() -> None:
    with pytest.raises(ValueError, match="Out of range float values"):
        HtmlSafeJson().dumps({"n": float("nan")})


def test_the_indent_is_configurable() -> None:
    assert HtmlSafeJson(indent=None).dumps({"b": 1, "a": [1, 2]}) == '{"a": [1, 2], "b": 1}\n'
