## Title
feat(measure): measurement logs are forwarded into the ledger, once each, from a verified cursor

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) and 8.g (`:316-324`): measurements
join the ledger. Two kinds of writer cannot reach it directly and append to the family
measurement log instead (lane `gap-measure-gh-1`): vibey-gh's delivery commands (lane
`gap-measure-gh-2`) and vibey's database-less processes, the test harness first (lanes
`gap-measure-log-sink`, `gap-measure-test-runs`). This lane moves a log's records into the
ledger through the process's `MeasurementPort` (lane `gap-measure-ledger-sink`), resuming from a
cursor so each record is forwarded once. The cursor names the last forwarded record's digest; a
log rewritten under it is refused, never re-read from an arbitrary place. A record that does not
decode is itself recorded as a failed ingest — never a silent omission.

Delivery is at-least-once: a crash between the ledger append and the cursor write repeats one
record. Readers count each `measurement_id` once (`MeasurementSeries.unique`, lane
`gap-measure-domain`), which is how the append-only ledger absorbs a replay.

## Required behaviour
1. New `src/vibey/infrastructure/measure/log_ingest.py`:
   - `@dataclass(frozen=True, slots=True) class IngestReport`: `read: int`, `recorded: int`,
     `skipped: int` (records at or before the cursor), `malformed: tuple[str, ...]`.
   - `class FileIngestCursor`: the cursor of `log` is the file `log.with_name(log.name +
     ".ingested")`.
     - `load(self, log: Path) -> tuple[int, str] | None`: missing file → `None`; otherwise a JSON
       object with an `int` (not `bool`) `seq >= 1` and a `str` `digest`, else
       `ValueError(f"ingest cursor {cursor} is not a cursor")`.
     - `save(self, log: Path, seq: int, digest: str) -> None`: writes
       `{"seq": seq, "digest": digest}` to a temporary file in the same directory, `chmod 0o600`,
       then `os.replace` (atomic).
   - `class MeasurementLogIngester`: `__init__(self, measurements: MeasurementPort, *, clock:
     Clock, log: MeasurementLogInterface | None = None, cursor: IngestCursorInterface | None =
     None, codec: MeasurementCodecInterface = MEASUREMENT_CODEC, ids: Callable[[], UUID] =
     uuid4)`; `log` defaults to `vibey_gh.measurement_log.MeasurementLog()`, `cursor` to
     `FileIngestCursor()`.
     `async def ingest(self, path: Path) -> IngestReport`:
     - `records = await asyncio.to_thread(self._log.read, path)` (a broken chain raises);
     - `position = self._cursor.load(path)`; when set, `seq > len(records)` or
       `records[seq - 1]["digest"] != digest` raises `ValueError(f"measurement log {path} no
       longer matches its ingest cursor at seq {seq}; it was rewritten or replaced")`;
     - for each record after the cursor, in order: `measurement =
       self._codec.decode(record["payload"])` and `await self._measurements.record(measurement)`;
       a `MalformedMeasurement` instead records `Measurement(subject=MeasurementSubject(
       SubjectKind.LANE, "vibey.measure.ingest"), outcome=FAILED, started_at=now,
       ended_at=now, detail=f"{path.name} seq {seq}: {exc}"[:500], measurement_id=ids())` and is
       listed in `malformed`; either way `self._cursor.save(path, seq, record["digest"])` follows
       the record. A failure of `record` propagates before the cursor moves.
     - returns the report.
2. New `src/vibey/infrastructure/measure/interfaces/log_ingest_interface.py`:
   `IngestCursorInterface` (`load`, `save`), `MeasurementLogIngesterInterface` (`ingest`) and the
   value contract `IngestReportInterface` (the four properties).

## Where to change
- New `src/vibey/infrastructure/measure/log_ingest.py` and its interface file.
- New `tests/infrastructure/measure/test_log_ingest.py`: real `MeasurementLog` and
  `FileIngestCursor` on `tmp_path`, `InMemoryMeasurements`, `FakeClock`.

## Acceptance criteria
- [ ] A log of three measurements ingests as `read 3, recorded 3, skipped 0`; ingesting again
      gives `read 3, recorded 0, skipped 3` and records nothing.
- [ ] Two more appended after the first ingest are the only ones the second records.
- [ ] A payload with a bad `started_at` (appended through the log, which only checks schema and
      id) is recorded as one `vibey.measure.ingest` `failed` measurement naming its seq, and the
      cursor moves past it.
- [ ] A cursor whose digest no longer matches, or whose seq is past the end, raises `ValueError`
      and records nothing.
- [ ] A sink that raises leaves the cursor where it was; the next ingest retries that record.
- [ ] **Cross-family contract:** a `vibey_gh.command_meter.CommandMeter(path=log)` run of
      `("merge-train", None, lambda: 0)` ingests as one `LANE` measurement named
      `vibey-gh.merge-train` with outcome `ok`.
- [ ] The cursor file is mode `0o600`; 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_log_ingest.py`:
- `test_a_log_is_forwarded_once`
- `test_only_new_records_are_forwarded`
- `test_a_malformed_record_is_recorded_as_a_failed_ingest`
- `test_a_rewritten_log_is_refused` (parametrized: digest changed, cursor past the end)
- `test_a_sink_failure_does_not_move_the_cursor`
- `test_a_malformed_cursor_is_refused`
- `test_vibey_gh_measurements_ingest` (the contract)
- `test_the_cursor_is_private_and_written_atomically`
- `test_the_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The `vibey measure ingest` command (`gap-measure-cli`); shipping a CI runner's log to a
  machine that ingests it (an operator decision).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): measurement logs are forwarded into the ledger, once each, from a verified cursor`. Do not push.

## Lane card
- **Depends on:** `gap-measure-log-sink`, `gap-measure-gh-2`.
- **Must keep passing unchanged:** every vibey-gh test and the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
