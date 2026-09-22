## Title
test(fakes): an in-memory append-only ledger that numbers, redacts and digests like PostgreSQL, under the real phase views

## Why
The event ledger is faked 17 times, and never the same way twice:
- `FakeLedger` ×7;
- `FakeDeployLedger` ×4;
- `FakeReviewLedger`, `FakeReviewTriageLedger` and `FakeReviewDeploymentLedger` ×2 each;
- `FakeReviewCollectLedger` and `FakeDesignLedger` ×2;
- `_RecordingLedger` ×2 (`tests/application/test_build_engine_run.py:32-34`, `test_engine_selection.py:817-`);
- `_FakeLedgerReader` and `_RecordingLedgerWriter` in `tests/application/test_wind_down.py:95-120`.

None of them does what the real append does (`src/vibey/infrastructure/db/ledger_repository.py:98-148`
and the `append_event` SQL in `migrations/0002_event.sql`):
- per-project `seq` from 1;
- redaction before persistence (`redact_payload`, `infrastructure/ledger/redact.py:54`);
- a digest over the redacted payload (`digest_event`, `domain/ledger.py:213`);
- append-only.

One fact makes a single fake enough. `PostgresBuildLedger` (`db/build_ledger.py:14-42`),
`PostgresDesignLedger` (`db/design_ledger.py:16-76`) and `PostgresReviewLedger`
(`db/review_ledger.py:19-58`) never touch a pool. They only call `.append(draft)` and
`.all_for_project(...)` on the `PostgresLedgerRepository` they are given. Given an in-memory
ledger, the **real** views run with no database, so the tests exercise production code rather
than a copy of it.

## Required behaviour
1. **A declared seam for the event store.** In
   `src/vibey/infrastructure/db/interfaces/ledger_repository_interface.py`, add
   `@runtime_checkable class LedgerRepositoryInterface(Protocol)` with `append`, `range`,
   `all_for_project` and `latest_seq`, using the exact signatures of
   `PostgresLedgerRepository` (`:150-190`).
   - Retype the constructor parameter `ledger` of `PostgresBuildLedger`,
     `PostgresDesignLedger` and `PostgresReviewLedger` from `PostgresLedgerRepository` to
     `LedgerRepositoryInterface`. Nothing else in the three classes changes.
   - Add `LedgerRepositoryInterface` to `DRIVER_SEAMS`.
2. **`tests/fakes/ledger.py` — `class InMemoryLedger`** implements
   `LedgerRepositoryInterface` and `LedgerReader`:
   - `append(draft)`:
     - `payload = redact_payload(draft.payload)`;
     - `digest = digest_event(payload)`;
     - `seq` is the project's `latest_seq + 1`;
     - `event_id` is `uuid4()`;
     - every other field is copied from the draft. It is stored and returned as a `LedgerEvent`.
   - `range(project_id, *, from_seq, to_seq)` includes both ends and sorts by `seq`.
   - `all_for_project` sorts by `seq`.
   - `latest_seq` returns 0 when the project has no events.
   - `events` is a read-only tuple property over every project, in append order.
   - Fault injection: `fail_next_append(exc: BaseException)` makes the next `append` raise
     `exc` and store nothing. `_RecordingLedger(fail=True)` becomes this.
   - There is no method that updates or deletes. The ledger is append-only (CLAUDE.md).
3. **`class InMemoryHandoffStore`** implements `HandoffStore`. It mirrors
   `PostgresHandoffRepository.record`, `get` and `list_for_pair` (`db/handoff_repository.py:34-113`):
   - `record` stores the envelope and returns `envelope.handoff_id`. Recording the same id
     twice raises `ValueError`, as the primary key does;
   - `get` returns the stored mapping, or `None`;
   - `list_for_pair` filters as the SQL does.
4. **`tests/fakes/ledger.py` also builds the phase views**, as factories:
   - `build_ledger(ledger) -> PostgresBuildLedger`;
   - `design_ledger(ledger) -> PostgresDesignLedger`;
   - `review_ledger(ledger, phase=Phase.REVIEW) -> PostgresReviewLedger`;
   - `deploy_review_ledger(ledger) -> PostgresReviewLedger` (phase `DEPLOY_REVIEW`).
   These are thin functions over the real classes. They are module functions, with this
   reason at the definition: "factories over production classes, kept beside the fake they
   wire".
5. **Registry.**
   - `LedgerReader` and `LedgerRepositoryInterface` → `InMemoryLedger()`.
   - `HandoffStore` → `InMemoryHandoffStore()`.
   - `BuildLedger` → `build_ledger(InMemoryLedger())`.
   - `DesignLedger` → `design_ledger(InMemoryLedger())`.
   - `PhaseLedger` → `review_ledger(InMemoryLedger())`.
   - Delete the five `PENDING` lines.
6. **Switch the ledger-centric tests:**
   - `tests/application/test_wind_down.py`: `_FakeLedgerReader` becomes an `InMemoryLedger`
     seeded by appending drafts built from the test's events (use `to_drafts`,
     `ledger_repository.py:196-`). `_FakeHandoffStore` becomes `InMemoryHandoffStore`.
     `_RecordingLedgerWriter` is a callable collaborator, not a port, so leave it;
   - `test_build_engine_run.py` and `test_engine_selection.py`: `_RecordingLedger` becomes
     `build_ledger(InMemoryLedger())`, with assertions on `ledger.events`, or on
     `fail_next_append` for the failing case.
   The other ledger doubles move in the domain lanes.

## Where to change
- `src/vibey/infrastructure/db/interfaces/ledger_repository_interface.py`,
  `src/vibey/infrastructure/db/build_ledger.py`, `design_ledger.py`, `review_ledger.py`
  (one annotation and one import each).
- New `tests/fakes/ledger.py`, `tests/fakes/test_fake_ledger.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/application/test_wind_down.py`, `test_build_engine_run.py`, `test_engine_selection.py`.

## Acceptance criteria
- [ ] `uv run mypy --strict src/vibey` passes with the retyped views.
- [ ] `PostgresLedgerRepository` satisfies `LedgerRepositoryInterface` (`isinstance` on an
      instance built with `pool=object()`).
- [ ] An `InMemoryLedger` event for a payload containing a secret-looking key has the same
      `payload` and `digest` as `redact_payload` and `digest_event` give.
- [ ] The registry has no `PENDING` entry naming `fakes-ledger`.

## Tests to write first (TDD)
`tests/fakes/test_fake_ledger.py`:
- `test_seq_is_per_project_and_starts_at_one`
- `test_payload_is_redacted_before_it_is_digested`
- `test_range_is_inclusive_and_ordered`
- `test_latest_seq_of_an_empty_project_is_zero`
- `test_a_failed_append_stores_nothing`
- `test_no_update_or_delete_is_offered` (`not hasattr(InMemoryLedger, name)` for `update`, `delete`, `remove`, `clear`)
- `test_the_real_build_view_writes_through_the_fake`
- `test_the_real_design_view_reads_back_design_events`
- `test_handoff_store_refuses_a_duplicate_id`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Ledger search and publication (`fakes-ledger-publication`).
- The per-domain ledger doubles (`fakes-design`, `fakes-build`, `fakes-review-visual`, `fakes-deploy`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-projects`. Its `LedgerAppender` Protocol is satisfied by `InMemoryLedger`.
  Add one test showing `InMemoryProjectRepository(ledger=InMemoryLedger())` ledgers a transition.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_ledger_repository.py`,
  `test_build_ledger.py`, `test_design_ledger.py`, `test_review_ledger.py` (integration),
  `tests/domain/test_noloss*.py` (protected).
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

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
