## Title
test(fakes): SQL that only PostgreSQL can evaluate is replayed from transcripts recorded against PostgreSQL, and a stale transcript fails

## Why
Some of `infrastructure/db` is SQL text that no Python fake can honestly evaluate. SQLite is
forbidden (ADR-0002), and it would evaluate a different dialect anyway:
- `migrator.py` runs the `migrations/*.sql` files, takes `pg_advisory_lock`, and reads `pg_locks` (`:98-232`);
- `advisory_lock.py` calls `pg_try_advisory_lock` and `pg_advisory_unlock` (`:28-54`);
- `ledger_repository.py:98-148` calls the `append_event(...)` SQL function (`migrations/0002_event.sql`);
- `ledger_search_repository.py:122-148` executes compiled SQL with `ILIKE … ESCAPE`;
- `notifier.py` uses `LISTEN`/`NOTIFY` through `conn.add_listener` (`:25-38`).

The version probe in `build_app` (`SHOW server_version_num`) is not here.
`fakes-bootstrap-seam` covers it through `PostgresResourcesFactory(pool_factory=...)`.

`fakes-db-unit-of-work` interprets ORM statements and refuses `text()`. For these, the
honest in-memory fake is a **replay of what PostgreSQL actually answered**. It is recorded by
the integration tier and replayed in the default tier. A digest of the migrations makes a
transcript fail the moment the schema moves under it. This is the only place in the design
where a fake's behaviour comes from a recording, and the amendment (A3) says so.

## Required behaviour
1. **`tests/fakes/sql_replay.py`**:
   - `class SqlTranscript` is a frozen dataclass: `schema_digest: str` and
     `exchanges: tuple[SqlExchange, ...]`. `SqlExchange` holds `sql` (whitespace-normalised),
     `params` (JSON-able), and exactly one of `rows`, `value`, `status` or `error`, where
     `error` is `{"type": ..., "sqlstate": ...}`. `load(path)` and `dump(path)` use the JSON
     under `tests/fixtures/sql_transcripts/<name>.json`.
   - `SchemaDigest.current()` is the sha256 over the sorted `migrations/*.sql` file names and
     contents.
   - `class ReplayConnection` implements the connection surface the modules above use:
     `execute`, `fetch`, `fetchrow`, `fetchval`, `transaction()`, `add_listener`,
     `remove_listener` and `close`. It uses the names of whatever driver seam
     `orm-unit-of-work` left for text SQL. Each call must equal the next exchange, compared on
     normalised SQL and params. Otherwise it raises `AssertionError` with a unified diff of
     expected versus actual. A replayed `error` raises the matching exception type.
     `deliver(channel, payload)` invokes the registered listeners, as a `NOTIFY` would.
   - `class RecordingConnection` wraps a real connection, forwards every call, and appends
     the exchange. `finish(path)` writes the transcript with the current schema digest.
2. **A declared connector seam** for the modules that open their own connection:
   `PostgresConnectorInterface` (`async connect(dsn: str) -> Any`) in
   `src/vibey/infrastructure/db/interfaces/connector_interface.py`, with production
   `ASYNCPG_CONNECTOR` (`db/connector.py`). If `fakes-cluster-preflight` has already added it,
   reuse it unchanged; otherwise add it, with the same names.
   `PostgresJobReadyNotifier(dsn, *, connector=ASYNCPG_CONNECTOR)` and the migrator take it.
   Add it to `DRIVER_SEAMS` if it is not there. Modules that take a pool or a unit of work are
   left as they are.
3. **Record and replay, one fixture.** `tests/infrastructure/db/conftest.py` gains a fixture
   `sql_session(request)`:
   - under `-m integration` with `VIBEY_TEST_RECORD_SQL=1`, it yields a `RecordingConnection`
     over the real one and writes the transcript, named by the test's node id with `/` and
     `::` replaced by `__`, at teardown;
   - in the default tier, it yields a `ReplayConnection` from that transcript. If the
     transcript is missing, the test is skipped with
     "no transcript; record with VIBEY_TEST_RECORD_SQL=1 -m integration". A missing
     transcript is never a pass.
4. **Convert the raw-SQL modules' tests to the fixture:** `test_migrator.py`,
   `test_advisory_lock.py`, `test_notifier.py`, `test_ledger_repository.py` (the append path)
   and `test_ledger_search_repository.py`. Record every transcript once, against a real
   PostgreSQL, and commit them.
   `test_chaos.py` (protected) and `test_keda_scaler_query.py`, which tests the chart's SQL
   against the server, stay integration-only.
5. **`tests/meta/test_sql_transcripts.py`**:
   - `test_every_transcript_matches_the_current_schema`: a digest mismatch fails and names the
     transcript and the command that re-records it;
   - `test_no_transcript_is_orphaned`: every file is used by a collected test.
6. The notifier's LISTEN path is replayed, and `deliver()` wakes the waiter. That gives
   `notifier.py` default-tier coverage.

## Where to change
- New `tests/fakes/sql_replay.py`, `tests/fakes/test_fake_sql_replay.py`,
  `tests/fixtures/sql_transcripts/*.json`, `tests/meta/test_sql_transcripts.py`.
- `src/vibey/infrastructure/db/interfaces/` (the connector seam), `db/notifier.py`, `db/migrator.py` (keyword injection).
- `tests/infrastructure/db/conftest.py`, the listed test modules,
  `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] With PostgreSQL stopped,
      `uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/db`
      passes, with no skip for a missing transcript.
- [ ] Editing one migration's comment makes `test_every_transcript_matches_the_current_schema` fail.
- [ ] Changing one SQL string in `advisory_lock.py` makes its replayed test fail with a diff.
- [ ] Together with `fakes-db-unit-of-work`, the default tier alone gives
      `coverage report --include='src/vibey/infrastructure/db/*' --fail-under=100`.
      Report the number in the commit body.

## Tests to write first (TDD)
`tests/fakes/test_fake_sql_replay.py`:
- `test_replay_answers_in_order`
- `test_replay_rejects_an_unexpected_statement_with_a_diff`
- `test_replay_raises_a_recorded_error`
- `test_deliver_invokes_listeners`
- `test_recording_round_trips_through_json`
- `test_schema_digest_changes_with_a_migration`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    VIBEY_TEST_RECORD_SQL=1 uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/db
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/db tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/db/*'
    git diff --stat HEAD~1 -- tests/infrastructure/db/test_chaos.py

## Out of scope
- Cluster preflight's probe (`fakes-cluster-preflight`).
- Using transcripts for anything the unit-of-work interpreter can evaluate.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-db-unit-of-work`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_chaos.py` (protected),
  `test_keda_scaler_query.py`, and the PostgreSQL 14–18 matrix.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).
  - The recording run needs PostgreSQL. It is the only step in any fakes lane that does, and it is the integration tier's job by definition.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
