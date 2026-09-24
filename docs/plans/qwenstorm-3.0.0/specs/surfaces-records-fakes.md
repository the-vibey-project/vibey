## Title
test(fakes): in-memory surface-operation and dead-letter stores, registered, and one contract binding them to PostgreSQL

## Why
The operator's standard (`STORM-CONTEXT.md`, "Operator standards"): "Every new seam gets a
registered in-memory fake"; draft amendment A2 (`specs/ADR-test-harness-fakes-amendment.md`)
defines "comprehensive" as passing the port's contract suite, "the same suite that binds the
real adapter in the opt-in tier", and A5 makes `tests/contracts/` that definition. The two
surface-lane stores (`surfaces-operation-repository`, `surfaces-dead-letter-repository`) are new
seams; every later surface-lane test (the guard, the reconciler, the requeue, the CLI) needs
them with no database. Part of ADR-0047 lanes S10–S12.

## Required behaviour
1. **`tests/fakes/surface_records.py`** (new):
   - `class InMemorySurfaceOperationRepository` implements
     `SurfaceOperationRepositoryInterface` over a dict keyed by `(surface, op_id)`, with the
     exact semantics of the PostgreSQL class: `start` wins once; `restart` moves only `failed`
     or `parked` rows, increments `attempts`, clears `detail`; `finish` stores
     `result` for `DONE` and `None` otherwise, clips `detail` to 2000 characters, refuses
     `STARTED`; `created_at`/`updated_at` come from an injected `clock: Clock` (default
     `tests.fakes.system.FakeClock()`).
     Fault injection: `fail_next(exc: BaseException)` makes the next call raise it and change
     nothing.
   - `class InMemorySurfaceDeadLetterRepository` implements
     `SurfaceDeadLetterRepositoryInterface`: `record` writes once per `(surface, dedupe_key)`
     with a fresh `uuid4()` id and `recorded_at` from the clock; `recent`, `get` and
     `mark_answered` behave as the PostgreSQL class (ordering, filters, `limit` bounds,
     answered once, evidence never rewritten); `fail_next(exc)` as above.
   - Neither class has a method body that is only `...`, `pass`, `return None` or
     `raise NotImplementedError`, and neither imports `unittest.mock`.
2. **Registry** (`tests/fakes/registry.py`): register
   `SurfaceOperationRepositoryInterface → InMemorySurfaceOperationRepository` and
   `SurfaceDeadLetterRepositoryInterface → InMemorySurfaceDeadLetterRepository`, and add both
   interfaces to `DRIVER_SEAMS`.
3. **Contract** `tests/contracts/test_surface_records_contract.py` (new): a module-level fixture
   parametrized over `backends()` from `tests/contracts/conftest.py`
   (`fakes-contracts-repositories`): `memory` builds the two fakes; `postgres` (integration)
   builds the two PostgreSQL repositories on `request.getfixturevalue("migrated_pool")`. The
   tests use only the interfaces' methods and assert every behaviour listed in 1.
4. **The meta test** `tests/contracts/test_every_repository_port_has_a_contract.py` (from
   `fakes-contracts-repositories`) gains both interfaces, naming this module.
5. If backends disagree, do not weaken a test: fix the fake, or report the PostgreSQL
   behaviour as a bug in the commit body.

## Where to change
- New `tests/fakes/surface_records.py`, `tests/contracts/test_surface_records_contract.py`.
- `tests/fakes/registry.py`, `tests/contracts/test_every_repository_port_has_a_contract.py` (append).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_surface_records_contract.py` passes with PostgreSQL stopped.
- [ ] `uv run pytest -q -p no:cacheprovider -m integration tests/contracts/test_surface_records_contract.py` passes on PostgreSQL.
- [ ] `tests/fakes/test_port_parity.py` passes (signatures, not-a-stub, `isinstance`).
- [ ] `fail_next` makes exactly one call raise and leaves the store unchanged.

## Tests to write first (TDD)
`tests/contracts/test_surface_records_contract.py` (both backends):
- `test_start_is_won_once`
- `test_finish_done_keeps_the_result_and_other_states_do_not`
- `test_restart_moves_failed_and_parked_only`
- `test_a_dead_letter_is_recorded_once_per_dedupe_key`
- `test_recent_orders_newest_first_and_hides_answered`
- `test_answering_is_once_and_keeps_the_evidence`
- `test_limits_and_empty_answerer_are_refused`
A no-backend test in the same module:
- `test_fail_next_raises_once_and_changes_nothing` (memory only, unmarked)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider -m integration tests/contracts/test_surface_records_contract.py

## Out of scope
- Production code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill
  trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-operation-repository`, `surfaces-dead-letter-repository`, `fakes-registry`, `fakes-contracts-repositories` (the `backends()` helper and the meta test), `fakes-observability` (`FakeClock`).
- **Shares a file with:** `tests/fakes/registry.py`, `tests/contracts/conftest.py` (read only).
- **Must keep passing unchanged:** every contract module, the fakes parity test, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port; `unittest.mock` is never used under `tests/fakes/`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
