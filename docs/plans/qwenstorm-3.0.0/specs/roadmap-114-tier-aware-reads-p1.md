## Title
feat(ledger): the jsonl+zlib segment codec seals a contiguous run of events and opens it back bit for bit

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, Acceptance "Bit-for-bit reconstruction from
mid-tier and archive forms, proven by property tests", Scope 5 "Reads are tier-aware", and
"Proposed child issues" 3). A sealed segment (`LedgerSegment`, lane
`roadmap-114-postgres-tier-store-p2`) names its `codec` and carries opaque `data`; something must
turn events into that data and back. Two facts fix the first format without waiting for the
codec benchmark (`roadmap-114-design-codec-chunking`):
- The ledger already has **one** per-event JSON object, "written one way and read back one way"
  so that the handoff ledger and the published shard "cannot drift apart"
  (`src/vibey/domain/ledger_record.py:2-8`), and one line codec every ledger file shares
  (`src/vibey/infrastructure/ledger/full_ledger_writer.py:23-56`, `LEDGER_LINES`). A segment's
  plaintext is those lines — the exact bytes `write_full_ledger` writes (`:59-66`).
- The only lossless codec that exists is `ZlibCodec(level=9)`
  (`src/vibey/infrastructure/ledger/compression.py:17-27`). The format is named by the segment's
  `codec` column, so the benchmark's choice later becomes another name, and a reader refuses a
  name it does not know.

Reading back must match the raw path, including forward compatibility: `EventRowMapper` reads a
kind, phase, engine or provenance a newer vibey wrote as its `Unrecognized*` value
(`src/vibey/infrastructure/db/ledger_repository.py:32-46`), whereas the strict record reader
refuses it (`src/vibey/domain/ledger_record.py:135-140`). So `open` returns rows shaped like
`event` rows, and callers map them with the same `EVENT_ROWS` (which takes a `Mapping` and a
decoded payload once `orm-ledger` has landed). A decode failure is the tier's own error,
`TierRecordError` (`src/vibey/infrastructure/ledger/tier_manager.py:31-32`). Codecs are pure
policies, not seams needing a fake (fakes amendment A4, `specs/ADR-test-harness-fakes-amendment.md`).
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) requires the lossless copy;
9.b (`doctrines.md:349`) the interface beside the class.

## Required behaviour
1. `src/vibey/infrastructure/ledger/segment_codec.py` (new):
   ```python
   """The `jsonl+zlib` ledger segment format (vibey#114).

   A segment's plaintext is the ledger's own record lines -- the one JSON object per event
   that the handoff ledger and the published shard already carry (`LEDGER_LINES`), each
   followed by a newline -- so a segment, a handoff ledger and a shard are one format. The
   plaintext is compressed with `ZlibCodec`. Another format is another codec name; a reader
   dispatches on the segment's `codec` and refuses a name it does not know.

   `open` returns rows shaped like `event` rows (ids as UUIDs, `produced_at` as an aware
   datetime, the payload decoded), not events: the caller maps them with the row mapper every
   reader of the ledger shares (`EVENT_ROWS`), so a value a newer vibey wrote reads back as
   its `Unrecognized*` type exactly as it does from a raw row.
   """
   ```
   - `JSONL_ZLIB: Final = "jsonl+zlib"`.
   - `class LedgerSegmentCodec:` with
     `__init__(self, *, lines: LedgerLinesInterface = LEDGER_LINES, compression: CompressionCodecInterface = DEFAULT_CODEC, name: str = JSONL_ZLIB) -> None`.
   - `@property name -> str`: the codec name it seals under and opens.
   - `seal(self, project_id: UUID, events: Sequence[LedgerEvent]) -> LedgerSegment`:
     `ordered = sorted(events, key=attrgetter("seq"))`; raise `ValueError` (and seal nothing)
     when `ordered` is empty (`"a ledger segment holds at least one event"`), when any event's
     `project_id != project_id` (`f"events {seqs} belong to another project than {project_id}"`),
     or when the seqs are not exactly `range(first, last + 1)`
     (`f"a ledger segment holds a contiguous run of seqs, not {seqs}"`). Otherwise
     `plaintext = "".join(self._lines.encode(event) + "\n" for event in ordered).encode("utf-8")`
     and return `LedgerSegment.seal(project_id=project_id, first_seq=first, last_seq=last, codec=self._name, data=self._compression.compress(plaintext))`.
   - `open(self, project_id: UUID, segment: LedgerSegmentInterface) -> tuple[dict[str, Any], ...]`,
     with `where = f"{project_id}:{segment.first_seq}-{segment.last_seq}"`:
     1. `segment.codec != self._name` →
        `TierRecordError(f"ledger segment {where} uses codec {segment.codec!r}, which this reader does not know")`.
     2. `segment.project_id != project_id or not segment.intact` →
        `TierRecordError(f"ledger segment {where} failed its digest or identity check")`.
     3. In one `try`: `text = self._compression.decompress(segment.data).decode("utf-8")`;
        `rows = tuple(self._row(json.loads(line, parse_constant=self._refuse_constant)) for line in text.splitlines())`;
        `except Exception as exc:  # noqa: BLE001 - every codec reports corrupt bytes differently`
        (copy of `tier_manager.py:87`) → `raise TierRecordError(f"invalid ledger segment {where}") from exc`.
     4. If `[row["seq"] for row in rows] != list(range(segment.first_seq, segment.last_seq + 1))`
        or any `row["project_id"] != project_id` →
        `TierRecordError(f"ledger segment {where} identity mismatch")`.
     5. Return `rows`.
   - `@staticmethod _row(fields: object) -> dict[str, Any]`: unless `isinstance(fields, dict)`
     and `fields.keys() == RECORD_FIELDS` (`from vibey.domain.ledger_record import RECORD_FIELDS`),
     raise `ValueError("a segment line is not a ledger record")`; otherwise return
     `{**fields, "event_id": UUID(fields["event_id"]), "project_id": UUID(fields["project_id"]), "job_id": None if fields["job_id"] is None else UUID(fields["job_id"]), "causation_id": None if fields["causation_id"] is None else UUID(fields["causation_id"]), "correlation_id": UUID(fields["correlation_id"]), "produced_at": datetime.fromisoformat(fields["produced_at"])}`.
   - `@staticmethod _refuse_constant(name: str) -> object`: raise
     `ValueError(f"{name} is not a JSON number")` (as `LedgerLines._refuse_constant`,
     `full_ledger_writer.py:47-51`: PostgreSQL's `jsonb` cannot hold NaN, so a segment that does
     is corrupt).
   - `SEGMENT_CODEC: Final[LedgerSegmentCodecInterface] = LedgerSegmentCodec()` with the
     one-line comment "stateless, so one instance serves".
2. `src/vibey/infrastructure/ledger/interfaces/segment_codec_interface.py` (new), in the style
   of `interfaces/full_ledger_writer_interface.py` (types under `TYPE_CHECKING`):
   `@runtime_checkable class LedgerSegmentCodecInterface(Protocol)` with the `name` property,
   `seal(self, project_id: UUID, events: Sequence[LedgerEvent]) -> LedgerSegmentInterface` and
   `open(self, project_id: UUID, segment: LedgerSegmentInterface) -> tuple[dict[str, Any], ...]`,
   each with a one-line docstring. Export it from
   `src/vibey/infrastructure/ledger/interfaces/__init__.py` (`__all__` alphabetical).
3. Nothing imports `vibey.infrastructure.db.ledger_repository` from these two modules (the
   repository will import the merger that uses this codec; `roadmap-114-tier-aware-reads-p2`).

## Where to change
- `src/vibey/infrastructure/ledger/segment_codec.py` (new; line 1 is the provenance comment
  copied byte-for-byte from line 1 of `src/vibey/infrastructure/ledger/compression.py`).
- `src/vibey/infrastructure/ledger/interfaces/segment_codec_interface.py` (new; same line 1 —
  line 1 only: do not copy `compression_interface.py`'s duplicated second header line).
- `src/vibey/infrastructure/ledger/interfaces/__init__.py` (`edit_file`).
- `tests/infrastructure/ledger/test_segment_codec.py` (new; same line 1).

## Acceptance criteria
- [ ] For every generated ledger, `tuple(EVENT_ROWS.to_event(row) for row in SEGMENT_CODEC.open(pid, SEGMENT_CODEC.seal(pid, events)))` equals the events, and each re-encodes to the same `LEDGER_LINES` line.
- [ ] `zlib.decompress(segment.data)` equals the bytes `write_full_ledger` writes for the same events.
- [ ] A kind this vibey does not know reads back as `UnrecognizedEventKind` with its text.
- [ ] Every refusal above raises `TierRecordError` (open) or `ValueError` (seal).
- [ ] `lint-imports` green; `mypy --strict src/vibey` clean; 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/ledger/test_segment_codec.py` (no service). Copy the style of
`tests/infrastructure/ledger/test_unrecognized_kinds_property.py:1-40`. Define in the module:
`PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000114")`, `T0 = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)`,
`PAYLOADS = st.dictionaries(st.text(max_size=8), st.one_of(st.none(), st.booleans(), st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.text(max_size=20)), max_size=4)`,
a helper `_event(seq, payload, *, kind=EventKind.TURN_COMPLETED, job_id=None, causation_id=None) -> LedgerEvent`
(fields as in `tests/infrastructure/ledger/test_tier_manager.py:34-50`, `digest=digest_event(payload)`,
`produced_at=T0 + timedelta(seconds=seq)`), and a composite strategy
`ledgers()` drawing `n` in `1..30` payloads and returning `tuple(_event(seq, p) for seq, p in enumerate(payloads, start=1))`.
- `test_the_codec_is_its_declared_seam` — `isinstance(SEGMENT_CODEC, LedgerSegmentCodecInterface)`; `SEGMENT_CODEC.name == "jsonl+zlib"`.
- `test_a_sealed_ledger_opens_back_bit_for_bit` — `@settings(deadline=None) @given(ledgers())`: seal, open, map with `EVENT_ROWS.to_event`; equal to the events; `[LEDGER_LINES.encode(e) for e in back] == [LEDGER_LINES.encode(e) for e in events]`; `segment.intact`; `(segment.first_seq, segment.last_seq) == (1, len(events))`.
- `test_the_plaintext_is_the_handoff_ledger_format` — for three events and `tmp_path`: `write_full_ledger(events, tmp_path / "ledger.jsonl")`; `(tmp_path / "ledger.jsonl").read_bytes() == zlib.decompress(SEGMENT_CODEC.seal(PROJECT, events).data)`.
- `test_a_kind_this_vibey_does_not_know_reads_back_unrecognized` — one event with `kind=EVENT_KIND_PARSER.parse("FutureKindX")`; the mapped event's kind is an `UnrecognizedEventKind` whose `.value == "FutureKindX"`.
- `test_job_and_causation_ids_survive` — one event with both set to fixed UUIDs; they read back equal.
- `test_seal_refuses_an_empty_foreign_or_gapped_run` — parametrize: `()`, one event of another project, events with seqs 1 and 3; each `pytest.raises(ValueError)`.
- `test_an_unknown_codec_name_is_refused` — `dataclasses.replace(segment, codec="zstd-19")`; `TierRecordError` matching `does not know`.
- `test_another_projects_or_rotted_segment_is_refused` — `open(uuid4(), segment)` and `open(PROJECT, dataclasses.replace(segment, data=segment.data + b"x"))` each raise `TierRecordError` matching `digest or identity`.
- `test_bytes_that_do_not_decompress_are_refused` — `LedgerSegment.seal(project_id=PROJECT, first_seq=1, last_seq=1, codec="jsonl+zlib", data=b"not zlib")`; `TierRecordError` matching `invalid ledger segment`.
- `test_a_line_that_is_not_a_record_or_carries_nan_is_refused` — parametrize plaintexts `b'["x"]\n'`, `b'{"a": 1}\n'`, `b'{"a": NaN}\n'`, each sealed with `data=zlib.compress(plaintext)`; `TierRecordError`.
- `test_lines_that_do_not_match_the_segment_range_are_refused` — seal events 1..3, then `LedgerSegment.seal(project_id=PROJECT, first_seq=1, last_seq=4, codec="jsonl+zlib", data=that.data)`; `TierRecordError` matching `identity mismatch`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Focused (no service is used by these tests; today the root conftest still opens the database at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/ledger
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Merging segments into ledger reads (`roadmap-114-tier-aware-reads-p2`, `-p3`); storing them
  (`roadmap-114-postgres-tier-store-p4`).
- Any other codec, chunk size, content address or chain-link manifest
  (`roadmap-114-design-codec-chunking`); the existing `TierManager` and its per-seq records.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
