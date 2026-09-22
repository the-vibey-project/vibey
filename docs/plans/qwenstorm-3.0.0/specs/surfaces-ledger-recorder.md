## Title
feat(surfaces): every surface operation made for a project is written to that project's ledger, redacted, with the redactions recorded

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md`, "7.c — the thorough ledger"): "the
ledger always holds as much of what happened as can be recorded … every job, run, turn, tool
call, decision, capacity signal, cost, measurement (8.g) and outcome, with its time, its actor
and its evidence, written as it happens … secrets, credentials and people's private details are
redacted where they would appear, and the redaction is itself recorded — never a silent
omission." 8.g: "Measurements join the ledger (7.c)." Draft ADR-0047 keeps `surface_operation`
and `surface_dead_letter` as operational state, "not the ledger" (§9) — so without this lane no
surface operation would ever reach the ledger.

The ledger is project-scoped (`LedgerEvent.project_id`, `cycle`, `phase` are required,
`src/vibey/domain/ledger.py`; `LedgerEventDraft`, `src/vibey/infrastructure/engines/tailer.py:36-52`).
A request carries its caller's project when the caller bound one (`surfaces-caller-scope`), and
the lane reads the project's current cycle and phase from the project store. An operation with
no project is measured and logged (`surfaces-lane-meter`) but cannot be ledgered until the
ledger has a deployment scope; that gap is stated, not hidden (10.f). The events are
append-only and never updated (non-negotiable).

## Required behaviour
1. **`src/vibey/domain/ledger.py`**: `EventKind` gains, after `DELIVERY_ESTIMATE_RECORDED`,
   with a one-line comment each:
   - `SURFACE_OPERATION_RECORDED = "SurfaceOperationRecorded"` — one surface operation's
     outcome and its measurement;
   - `SURFACE_OPERATION_PARKED = "SurfaceOperationParked"` — a dead letter recorded as a park;
   - `SURFACE_OPERATION_REQUEUED = "SurfaceOperationRequeued"` — a person granted a parked
     operation.
2. **`src/vibey/infrastructure/surface_lanes/ledger_recorder.py`**, `class SurfaceLedgerRecorder`:
   `__init__(self, *, ledger: LedgerRepositoryInterface, projects: ProjectStore, clock: Clock, logger: Logger, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION, redactor: SurfaceRequestRedactorInterface = SURFACE_REDACTOR, catalogue: SurfaceCatalogueInterface = CATALOGUE)`.
   - `async record_outcome(self, request: SurfaceRequest, outcome: OperationOutcome, *, instance: str) -> bool`:
     1. no `request.caller.project_id` → log `surface.operation.unledgered` at `debug`
        (surface, operation, op_id) and return False;
     2. `project = await projects.get(project_id)`; `None`, or a phase that is not a known
        `Phase`, → log `surface.operation.unledgered` at `warning` with the reason, return False;
     3. `spec = catalogue.get(...)`; `redacted = redactor.for_ledger(spec, request.args)`;
        `result, result_redactions = redactor.result_for_ledger(spec, outcome.result)`;
     4. payload (exact keys): `surface`, `operation`, `op_id`, `request_id`, `status`,
        `replayed`, `attempts`, `instance`, `detail`, `args` (redacted),
        `result` (redacted), `redactions` (list of `{"path", "class"}` from both),
        `wait_ms` (`(outcome.started_at - request.requested_at)` in ms, or `None`),
        `service_ms` (`(outcome.finished_at - outcome.started_at)` in ms, or `None`);
     5. `await ledger.append(LedgerEventDraft(project_id, cycle=project.cycle, phase=project.phase, kind=EventKind.SURFACE_OPERATION_RECORDED, engine_id=None, job_id=request.caller.job_id, causation_id=None, correlation_id=correlation.for_project(project_id).value, provenance=Provenance.TRUSTED, produced_at=clock.now(), payload=payload, digest=digest_event(payload)))`;
     6. any exception from the ledger is logged as `surface.ledger_failed` at `error` and
        returns False: the operation already happened, and failing its delivery would repeat it.
   - `async record_parked(self, dead: SurfaceDeadLetter, caller: SurfaceCaller) -> bool`: the
     same flow with kind `SURFACE_OPERATION_PARKED` and payload `surface`, `operation`, `op_id`,
     `request_id`, `reason`, `detail`, `attempts`, `delivery_count`, `instance`,
     `dead_lettered_at` (ISO), `retained`, `args` (redacted for the ledger from
     `dead.request["args"]`), `redactions`.
   - `async record_requeued(self, *, surface: str, operation: str, op_id: str, dead_letter_id: UUID, new_request_id: str, answered_by: str, caller: SurfaceCaller) -> bool`:
     kind `SURFACE_OPERATION_REQUEUED`, payload with those fields (the person's name as given).
3. **`src/vibey/infrastructure/surface_lanes/interfaces/ledger_recorder_interface.py`**:
   `@runtime_checkable class SurfaceLedgerRecorderInterface(Protocol)` with the three methods;
   exported. Registry: `SurfaceLedgerRecorderInterface →` the real class over
   `InMemoryLedger()` and `InMemoryProjectRepository()` (fakes-ledger, fakes-projects), in
   `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- `src/vibey/domain/ledger.py` (three enum members).
- New `src/vibey/infrastructure/surface_lanes/ledger_recorder.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/ledger_recorder_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_ledger_recorder.py`.

## Acceptance criteria
- [ ] For a `secrets.set_secret` made inside `bind(project_id=P, job_id=J)`, one `SurfaceOperationRecorded` event lands in P's ledger at P's cycle and phase, with `job_id=J`, the delivery's correlation id, provenance `trusted`, and **no** plaintext secret anywhere in the stored payload; `redactions` lists `args.value` as `sensitive`.
- [ ] For `email.send_email`, the recipient, subject and body appear only as digests, each listed as `personal`.
- [ ] `wait_ms` and `service_ms` are computed from the request and outcome times.
- [ ] No project → no event and a debug line; an unknown project or phase → no event and a warning; a failing ledger (`InMemoryLedger.fail_next_append`) → False and an error line, never an exception.
- [ ] `record_parked` and `record_requeued` write their kinds with the listed payload keys.
- [ ] The three new kinds round-trip through `EVENT_KIND_PARSER`; `tests/domain/test_ledger.py` and the forward-compatibility tests pass unchanged; 100% branch coverage of `domain/` and `infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_ledger_recorder.py` (no service; `InMemoryLedger`, `InMemoryProjectRepository`, `FakeClock`, `RecordingLogger`):
- `test_a_project_operation_is_ledgered_at_its_cycle_and_phase`
- `test_secrets_never_reach_the_ledger_and_the_redaction_is_listed`
- `test_personal_details_are_digested`
- `test_measurements_ride_in_the_event`
- `test_no_project_is_logged_not_ledgered`
- `test_an_unknown_project_is_a_warning`
- `test_a_failing_ledger_never_raises`
- `test_parks_and_requeues_are_ledgered`
- `test_new_kinds_parse`
- `test_recorder_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/domain tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- A deployment-scoped ledger for project-less operations (owed to the 8.g measurement epic,
  `issue-audit/gaps.md` D1). The publication allowlist for the new kinds
  (`src/vibey/domain/publication_policy.py`; unlisted kinds stay unpublished). CHANGELOG.md,
  docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not
  push, open PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-redaction`, `surfaces-protocol`, `surfaces-caller-scope`, `surfaces-operation-handler` (`OperationOutcome`), `fakes-ledger` (`LedgerRepositoryInterface`, `InMemoryLedger`), `fakes-projects` (`InMemoryProjectRepository`), `fakes-observability`.
- **Shares a file with:** `src/vibey/domain/ledger.py` (append members after the last), `tests/fakes/registry.py`.
- **Must keep passing unchanged:** `tests/domain/test_ledger*.py`, `tests/domain/test_forward_compatible_readers.py`, `tests/infrastructure/ledger/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - The ledger is append-only: never add a method that updates or deletes an event.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
