## Title
feat(test-harness): one store per machine for requests, answers, attempts and dead letters

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:283-286`): a dead-lettered run
is kept "with its evidence, where a human or a repair lane can see it — it is never retried
forever and never silently dropped". Draft ADR-0045 §3 and §9 decide the harness's own records
live in **one file store per machine** under `state_dir`, shared by both backends, so choosing
either can never split the record; PostgreSQL is deliberately not the harness's store (per
machine, must work with nothing running but the tests, one store keeps both backends coherent),
and the store is a port so an ORM adapter can be added later without touching the protocol.

Readers run outside the lock (the requester's fast path, `vibey test status`), so every write is
atomic. An attempt number is claimed with `os.link`, which is atomic and fails if the name is
taken, so no reader ever sees a half-written file. A terminal attempt is never rewritten, and an
answer to a dead letter is a new file (the append-only discipline of CLAUDE.md).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/file_store.py`, using harness-T03's
`TestHarnessCodec` / `MalformedTestHarnessMessage` (`vibey.domain.test_harness_protocol`) and
harness-T04's `TestRunRecordCodec`, `TestRunRecord`, `DeadLetter`, `DeadLetterAnswer`
(`vibey.domain.test_run_record`), through their interfaces:
1. **`AtomicFile`**, a stateless class: `write(self, path: Path, data: bytes) -> None` writes a
   temporary file in `path.parent` (mode `0o600`), then `os.replace`s it onto `path`.
2. **`FileTestRunStore(root: Path, *, messages: TestHarnessCodecInterface, records: TestRunRecordCodecInterface)`**.
   `ensure(self) -> None` creates `root` and its subdirectories `requests`, `answers`, `runs`,
   `running`, `logs`, `data`, `dead` and `malformed`, each mode `0o700`. Every file is mode `0o600`.
3. **Requests** (the `local` hand-off): `put_request(request) -> Path` writes
   `requests/<request_id>.json`; `take_request(path) -> TestRunRequest` decodes it, raising
   `MalformedTestHarnessMessage` for a malformed file or a file that holds a result.
4. **Answers**: `put_answer(result)` writes `answers/<request_id>.json`;
   `answer(request_id: UUID) -> TestRunResult | None`; `recent_answers(limit: int) -> tuple[TestRunResult, ...]`,
   newest first by mtime, skipping (and logging a warning through `structlog.get_logger(__name__)`,
   as other infrastructure modules do) any file that fails to decode.
5. **Attempts** at `runs/<key[:2]>/<key>/<attempt:06d>.json`:
   - `begin(record) -> TestRunRecord`: `n = 1 + (highest existing attempt number, or 0)`; write
     `dataclasses.replace(record, attempt=n)` to a temporary file; `os.link(tmp, final)`; on
     `FileExistsError` try `n + 1`; unlink the temporary file; write the marker
     `running/<run_id>.json` holding `{"key": key, "attempt": n}`; return the numbered record.
   - `finish(record)`: requires `record.outcome is not None` (else `ValueError`); writes the
     attempt file with `AtomicFile`, then removes the running marker.
   - `attempts(key) -> tuple[TestRunRecord, ...]`, sorted by attempt.
   - `attempts_as_recorded(key) -> tuple[RecordedAttempt, ...]`:
     `record.as_attempt(answered=self.is_answered(record.run_id))` for each attempt.
   - `running() -> tuple[TestRunRecord, ...]`: the attempts that have a running marker.
6. **Paths**: `log_path(run_id) -> Path` is `logs/<run_id>.log`;
   `supervisor_log_path(request_id) -> Path` is `logs/supervisor-<request_id>.log`;
   `data_dir(run_id) -> Path` is `data/<run_id>/`, created with mode `0o700`.
7. **Dead letters**:
   - `dead_letter(letter)` creates `dead/<run_id>.json` with the same `os.link` method; if the file
     exists already it does nothing;
   - `dead_letter_by_run(run_id) -> DeadLetter | None`;
   - `dead_letter_for_request(request_id) -> DeadLetter | None` scans `dead/*.json`, skipping `*.answer.json`;
   - `dead_letters(*, include_answered: bool = False) -> tuple[DeadLetter, ...]`, oldest first;
   - `answer_dead_letter(answer)` creates `dead/<run_id>.answer.json` with `os.link`; if it exists
     it raises `ValueError(f"dead letter {run_id} is already answered")`;
   - `is_answered(run_id) -> bool`.
8. **Malformed messages** (from harness-T23):
   `put_malformed(raw: bytes, *, message_id: str | None, reason: str, received_at: datetime) -> Path`
   writes `malformed/<uuid4>.bin` and a `.json` sidecar `{"message_id", "reason", "received_at"}`;
   `malformed() -> tuple[Path, ...]` lists the `.bin` files.
9. **Retention**: `prune(self, *, older_than: datetime) -> int` removes files older than the
   cutoff by mtime and returns how many it removed: finished attempt files (never one with a
   running marker); logs and data directories; answers and requests; and dead letters **that are
   answered**, together with their answer files. It never removes an unanswered dead letter.
10. **The interface** `src/vibey/infrastructure/test_harness/interfaces/file_store_interface.py`
    declares `@runtime_checkable` `TestRunStoreInterface` with every public method above
    (`ensure` included) and `AtomicFileInterface`. Later lanes type against `TestRunStoreInterface`.
11. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
    interface module, append `file_store_interface.TestRunStoreInterface` to `DRIVER_SEAMS`, and
    add `"TestRunStoreInterface": "fakes-test-harness"` to `PENDING` (fakes-test-harness registers
    `InMemoryTestRunStore`).

## Where to change
- New `src/vibey/infrastructure/test_harness/file_store.py` and its interface module.
- `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_file_store.py`.

## Acceptance criteria
- [ ] `begin` numbers attempts 1, 2, 3 per key. Two `begin` calls racing for one number (simulated by pre-creating the next file) both succeed with different numbers.
- [ ] `finish` removes the running marker, and `running()` stops listing the attempt.
- [ ] A dead letter is written once; a second write is a no-op; a second answer raises.
- [ ] `prune` keeps unanswered dead letters and running attempts, and removes everything else past the cutoff.
- [ ] Every file is `0o600` and every directory `0o700`.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_file_store.py` (`from vibey.infrastructure.test_harness import file_store as fs`),
with a helper class that builds requests and records through harness-T03 and T04; every store
root is under `tmp_path`:
- `test_request_round_trip_and_malformed_request`
- `test_answer_round_trip_and_recent_answers_order`
- `test_recent_answers_skip_undecodable_files`
- `test_begin_numbers_attempts_per_key`
- `test_begin_survives_a_taken_number`
- `test_finish_requires_an_outcome_and_clears_running`
- `test_attempts_as_recorded_marks_answered_dead_letters`
- `test_dead_letter_is_written_once`
- `test_dead_letter_lookup_by_run_and_by_request`
- `test_answering_twice_raises`
- `test_malformed_messages_are_kept`
- `test_prune_keeps_unanswered_dead_letters_and_running_attempts` (set old mtimes with `os.utime`)
- `test_file_modes`
- `test_store_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- A PostgreSQL (ORM) store: ADR-0045 §3 explains why the file store is the design; the port admits one later, and it would go through the `orm-*` seams.
- The in-memory store fake (fakes-test-harness).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T04-test-run-records, harness-T05-test-harness-config, fakes-registry.
- **Files touched:** the two new source files, `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only). Later harness lanes call `file_store.py` and never edit it.
- **Must keep passing unchanged:** the harness-T01–T05 tests, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Never touch the real machine state: every store root is under `tmp_path`.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
