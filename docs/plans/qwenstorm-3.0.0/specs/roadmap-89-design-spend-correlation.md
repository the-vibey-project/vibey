## Title
fix(cli): DESIGN spend events join their delivery and name the engine that actually ran

## Why
Issue #89 (rewrite: `issue-audit/updates/89.md`, Scope 7 "one correlation ID on every ledger event",
"Proposed child issues" 1). Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks the
ledger to hold what happened, with its actor; 10.f (`doctrines.md:419`) forbids a larger claim than
the evidence. `src/vibey/domain/correlation.py` derives one uuid5 per delivery
(`DeliveryCorrelation.for_project`, `correlation.py:55-66`; the shared deriver `DELIVERY_CORRELATION`
at `:80`). Every ledger write site uses it except one: `_build_spend_recorder` in
`src/vibey/cli/main.py:140-176` writes each DESIGN `BUDGET_SPENT` with
- `correlation_id=uuid4()` (`main.py:168`) — a random id, so DESIGN spend cannot be joined to its
  delivery; and
- `engine_id=EngineId.CLAUDELOOP` (`main.py:165`) — hard-coded, although the recorder is also built
  for the `opencode` provider (`main.py:452-462` in `_work_once`, `:1605-1624` in `worker`).
The static guard `tests/meta/test_correlation_ids_are_derived.py:28` carries exactly this site as
`KNOWN_REMAINING = {"cli/main.py": 1}`, and says "Deleting this entry is the whole of that
follow-up's test change".

## Required behaviour
1. `_build_spend_recorder(ledger: LedgerRepositoryInterface, project_id: UUID, cycle: int, phase: Phase, *, engine_id: EngineId) -> SpendRecorder`:
   - the parameter type becomes `LedgerRepositoryInterface`
     (`vibey.infrastructure.db.interfaces.ledger_repository_interface`, declared by lane
     `fakes-ledger`), so an in-memory ledger can be passed;
   - the new keyword-only `engine_id` is written as the event's `engine_id`;
   - `correlation_id=DELIVERY_CORRELATION.for_project(project_id).value`
     (`from vibey.domain.correlation import DELIVERY_CORRELATION`);
   - everything else in the draft (`kind=EventKind.BUDGET_SPENT`, the payload, provenance, digest)
     is unchanged.
2. Every call site passes the engine that the process it is built for runs:
   `EngineId.CLAUDELOOP` for the `ClaudeLoopProcess` sites (`main.py:~433`, `~1581`) and
   `EngineId.OPENCODE` for the `OpenCodeLoopProcess` sites (`main.py:~460`, `~1620`). (This corrects
   attribution of existing code; it adds nothing for OpenCode.)
3. If `uuid4` is no longer used anywhere else in `main.py`, remove it from the `from uuid import`
   line (`main.py:19`); `main.py:1255` has its own local import — leave it.
4. `tests/meta/test_correlation_ids_are_derived.py:28`: `KNOWN_REMAINING: dict[str, int] = {}`.
   Delete the comment paragraph at `:14-20` (it begins "# Sites this slice could not reach" and
   names `cli/main.py`); keep the COUNT paragraph at `:21-27`, which still explains the guard.

## Where to change
- `src/vibey/cli/main.py` (the function and its four call sites; use `edit_file`, the file is long).
- `tests/meta/test_correlation_ids_are_derived.py` (the constant and its comment).
- `tests/cli/test_operational_commands.py:2232-2234`: the existing call
  `_build_spend_recorder(resources.ledger, project.project_id, project.cycle, Phase.DESIGN)` gains
  `engine_id=EngineId.CLAUDELOOP` (one targeted edit; import `EngineId` inside the test as it
  imports `Phase`).
- New test file `tests/cli/test_spend_recorder.py`.

## Acceptance criteria
- [ ] `test_no_correlation_id_is_minted_with_uuid4` passes with `KNOWN_REMAINING = {}`.
- [ ] A recorded DESIGN spend's `correlation_id` equals `DELIVERY_CORRELATION.for_project(project_id).value`.
- [ ] A recorder built with `engine_id=EngineId.OPENCODE` writes `engine_id == EngineId.OPENCODE`.
- [ ] `test_recorded_spend_is_visible_to_the_budget_brake` (integration tier) still passes.
- [ ] 100% branch coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/cli/test_spend_recorder.py` (default tier; `InMemoryLedger` from `tests/fakes/ledger.py`,
lane `fakes-ledger`; no database, no patching):
- `test_design_spend_joins_its_delivery` — record `(2, 0.5)` for a project; the one event's
  `correlation_id == DELIVERY_CORRELATION.for_project(project_id).value`, kind `BUDGET_SPENT`,
  payload `{"turns": 2, "dollars": 0.5}`.
- `test_design_spend_names_the_engine_that_ran` — parametrized over `EngineId.CLAUDELOOP` and
  `EngineId.OPENCODE`; the event's `engine_id` is the one passed.
- `test_two_recorders_for_one_project_share_the_correlation` — two recorders, two events, one id.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_spend_recorder.py tests/meta/test_correlation_ids_are_derived.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    uv run pytest -q -p no:cacheprovider tests/cli/test_operational_commands.py -k recorded_spend   # needs PostgreSQL (integration)
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `CorrelationLogContext` (`roadmap-89-correlation-log-context`); every other ledger write site.
- Removing the OpenCode provider branches (ADR-0046 lanes L38/L39).
- Roles, audit, identity (#89 children 3–8, blocked on its open questions). Docs, CHANGELOG.
  Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
