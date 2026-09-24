## Title
feat(surfaces): guarded operations write an intent before the effect, so a send whose outcome is unknown is parked, never repeated

## Why
Draft ADR-0047 §8 (`specs/ADR-surface-lanes.md`, "Guarded operations"): `create_page`,
`send_email` and `send_sms` reach backends that cannot deduplicate ("What does not fit": "SMTP
and Kannel's sendsms have no idempotency key, so a repeated send is a second message.
BookStack's page create has none either"). Sub-doctrine 8.f: "an operation delivered twice
takes effect once — a message is sent once." So the lane writes an intent row **before** the
effect and a result row **after** it, and decides by the row it finds:

- none → insert `started`, execute;
- `done` → reply with the recorded result and `replayed=true`; nothing is sent again;
- `started` → an earlier delivery began and never finished; the outcome is unknown; **park**
  (reason `outcome_unknown`) and send nothing;
- `failed` → the previous attempt failed before any effect; executing again is safe;
- `parked` → answer `parked` at once, unless the request carries a grant (§9);
- a different `request_digest` under the same `op_id` → reject with "idempotency key reused
  with different arguments".

"The price is that a crash in the middle of a send asks a human, rather than guessing." This
lane is that protocol, over the store of `surfaces-operation-repository`. ADR-0047 lane S24.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/guarded.py`, `class SurfaceGuardedExecutor`
(implements `SurfaceExecutorInterface`, lane `surfaces-operation-handler`):

1. `__init__(self, *, operations: SurfaceOperationRepositoryInterface, handler: SurfaceExecutorInterface, instance: str, redactor: SurfaceRequestRedactorInterface = SURFACE_REDACTOR, catalogue: SurfaceCatalogueInterface = CATALOGUE)`.
2. `async execute(self, request: SurfaceRequest) -> OperationOutcome`:
   1. `spec = catalogue.get(...)`; a spec that is not `GUARDED` raises `ValueError` (the
      dispatcher routes only guarded operations here).
   2. `digest = redactor.request_digest(spec, request.args)`; `s = request.surface.value`.
   3. `row = await operations.get(s, request.op_id)`.
   4. **No row**: `won = await operations.start(surface=s, op_id=…, operation=…, request_digest=digest, request_id=request.request_id, instance=instance)`.
      If not `won` (another delivery raced it), re-read the row and continue at step 5 with it.
      If won, execute (step 6).
   5. **A row**:
      - `row.request_digest != digest` → `REJECTED`, `detail="idempotency key reused with different arguments"`,
        `dead_reason=KEY_REUSED`. Nothing runs.
      - `DONE` → `OK`, `result=row.result`, `replayed=True`,
        `detail="answered from the record of the first delivery"`.
      - `STARTED` → `PARKED`, `dead_reason=OUTCOME_UNKNOWN`,
        `detail="an earlier delivery began and never finished; the outcome is unknown"`;
        then `operations.finish(state=PARKED, detail=…)`. A grant does **not** override
        `started` (the first attempt may still be running).
      - `PARKED` without `request.grant` → `PARKED`, `dead_reason=None` (already recorded),
        `detail="parked earlier; a person must grant it (vibey surface requeue)"`.
      - `PARKED` with `request.grant`, or `FAILED` → `await operations.restart(...)`; if it
        returns False (a race), re-read and continue at step 5; else execute (step 6).
   6. **Execute**: `outcome = await handler.execute(request)`, then record it:
      - `OK` → `finish(state=DONE, result=outcome.result)`;
      - `PARKED` (outcome unknown) → `finish(state=PARKED, detail=outcome.detail)`;
      - `EXPIRED`, `REJECTED`, `ERROR` → `finish(state=FAILED, detail=outcome.detail)` (nothing
        reached the backend, or the handler proved the failure permanent before the effect).
      Return the handler's outcome.
   Persist before replying: the dispatcher replies only after `execute` returns (ADR-0044's
   "persist the result, then publish, then acknowledge").
3. `src/vibey/infrastructure/surface_lanes/interfaces/guarded_interface.py`:
   `@runtime_checkable class SurfaceGuardedExecutorInterface(SurfaceExecutorInterface, Protocol)`;
   exported. Registry: `SurfaceGuardedExecutorInterface → functools.partial(SurfaceGuardedExecutor, operations=InMemorySurfaceOperationRepository(), handler=<a SurfaceOperationHandler over InMemoryDocs>, instance="fake")`,
   in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/guarded.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/guarded_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_guarded.py`.

## Acceptance criteria
- [ ] First delivery of `email.send_email`: one intent row, one message in `InMemoryEmail`, row `done`.
- [ ] A redelivery (same `op_id`, same args, new `request_id`) returns `ok` + `replayed`, and `InMemoryEmail.sent` still has one message.
- [ ] A row left `started` (simulate a crash with `InMemorySurfaceOperationRepository.start` then no finish) makes the next delivery `parked` with `outcome_unknown`, sends nothing, and moves the row to `parked`.
- [ ] A later delivery without a grant is `parked` with no new dead reason; with `grant=True` it executes once and the row is `done`.
- [ ] Same `op_id`, different body → `rejected`, `key_reused`; nothing sent.
- [ ] A handler outcome of `parked` leaves the row `parked`; `error` leaves it `failed`, and the next delivery executes again.
- [ ] A lost `start` race re-reads and follows the row found.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_guarded.py` (no service; `InMemorySurfaceOperationRepository`, a real `SurfaceOperationHandler` over `InMemoryEmail`/`InMemoryDocs`, and a small scripted executor class for outcomes the in-memory adapters cannot produce):
- `test_first_delivery_records_intent_then_result`
- `test_a_redelivery_is_answered_from_the_record`
- `test_a_started_row_parks_and_sends_nothing`
- `test_parked_waits_for_a_grant_and_a_grant_runs_once`
- `test_a_reused_key_with_other_arguments_is_rejected`
- `test_handler_outcomes_are_recorded_by_state` (parametrized)
- `test_a_lost_start_race_follows_the_winner_s_row`
- `test_a_non_guarded_operation_is_refused`
- `test_executor_satisfies_its_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Dead-lettering a parked send and draining it into `surface_dead_letter` (`surfaces-dispatcher`,
  `surfaces-reconcile`); the grant command (`surfaces-requeue`). CHANGELOG.md, docs/, ADRs,
  CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open
  PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-operation-handler`, `surfaces-records-fakes`, `surfaces-redaction`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
