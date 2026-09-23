## Title
feat(worker): every log line a job emits carries its delivery's correlation id

## Why
Issue #89 (rewrite: `issue-audit/updates/89.md`, Scope 7 "one correlation ID on every ledger event
*and* log line", "Proposed child issues" 2). The ledger half is live: every write site derives the
id from `DeliveryCorrelation` (`src/vibey/domain/correlation.py:55-80`). The log half is built but
never entered — the class says so itself: `CorrelationLogContext`
(`src/vibey/infrastructure/logging.py:153-215`) "**Nothing in production enters this scope yet** …
The scope belongs at the job execution boundary in `WorkerLoop`, which cannot reach this class
directly: `application/` may not import `infrastructure/`, so wiring it needs an application-side
port and a binding in the composition root" (`logging.py:170-181`). `grep -rn CorrelationLogContext src`
finds only its definition, its interface and the conformance line `logging.py:221`. Sub-doctrine 7.c
(`src/vibey_tools/gh/docs/doctrines.md:82-91`) and 10.f (`doctrines.md:419`): "this delivery emitted
no correlated lines" and "nothing emits correlated lines yet" are different facts; this lane makes
the first one checkable.

## Required behaviour
1. `src/vibey/application/interfaces/observability.py`: add
   ```python
   @runtime_checkable
   class LogCorrelationScope(Protocol):
       """Binds a delivery's correlation id onto every log line inside a ``with`` block."""

       def bound(self, correlation_id: CorrelationIdInterface) -> AbstractContextManager[str]: ...
   ```
   (`AbstractContextManager` is already imported at `observability.py:13`; import
   `CorrelationIdInterface` from `vibey.domain.interfaces.correlation_interface`). Export it from
   `vibey.application.interfaces` beside the other observability ports.
   `CorrelationLogContext` already satisfies it structurally (`logging.py:198-215`).
2. `WorkerLoop.__init__` (`src/vibey/application/worker.py:61-95`) gains two keyword parameters,
   after `telemetry_enabled`:
   `log_scope: LogCorrelationScope | None = None` and
   `correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION` (copy the import and default
   from `application/build_implement_handler.py:45` and `:79`). Store them.
3. `WorkerLoop.run_once` (`worker.py:130-175`): the whole job execution — from
   `started_at = datetime.now(UTC)` through the settle of the outcome (ack, nack, park, defer and
   the notification) — runs inside
   `scope = self._log_scope.bound(self._correlation.for_project(project_id)) if self._log_scope is not None else contextlib.nullcontext()`
   (`contextlib` is already imported). The claim itself and the "nothing claimable" return stay
   outside. Behaviour with `log_scope=None` is byte-for-byte today's.
4. `src/vibey/bootstrap.py`: each of the three `WorkerLoop(` constructions (`bootstrap.py:215`,
   `:247`, `:626`) passes `log_scope=CorrelationLogContext()`
   (`from vibey.infrastructure.logging import CorrelationLogContext`).
5. `logging.py:170-181`: replace the "Nothing in production enters this scope yet" paragraph with
   one sentence saying the scope is entered by `WorkerLoop.run_once` for every claimed job, bound in
   `bootstrap.py`, and that log lines outside a job (startup, the idle poll) carry no id by design.
6. Register a fake for the new port: in `tests/fakes/observability.py` (lane `fakes-observability`)
   add `RecordingLogScope`, implementing `LogCorrelationScope`, whose `bound` records the id it was
   given in `self.bound_ids: list[str]` and yields `str(correlation_id.value)` while setting
   `self.active = True` for the duration; register it in `tests/fakes/registry.py`.

## Where to change
- `src/vibey/application/interfaces/observability.py` (+ its `__init__` export),
  `src/vibey/application/worker.py`, `src/vibey/bootstrap.py`, `src/vibey/infrastructure/logging.py`
  (docstring only). Use `edit_file`.
- `tests/fakes/observability.py`, `tests/fakes/registry.py` (the fake).
- Append tests to `tests/application/test_worker.py` and `tests/infrastructure/test_correlation_log_context.py`.

## Acceptance criteria
- [ ] A handler running under `WorkerLoop.run_once` sees
      `structlog.contextvars.get_contextvars()["correlation_id"] == str(DELIVERY_CORRELATION.for_project(project_id).value)`
      when the loop is built with `CorrelationLogContext()`.
- [ ] After `run_once` returns (success, failure or an exception inside the handler), the id is no
      longer bound.
- [ ] With `log_scope=None` every existing `test_worker.py` test passes unchanged.
- [ ] `grep -c "log_scope=CorrelationLogContext()" src/vibey/bootstrap.py` prints `3`.
- [ ] 100% branch coverage of `application/` and `infrastructure/`; import-linter green (application
      imports no infrastructure).

## Tests to write first (TDD)
Append to `tests/application/test_worker.py` (fakes: `FakeJobRepository`, `FakeHumanGateRepository`,
`make_job` — from `tests/fakes/queue.py` once `fakes-registry` has moved them, else
`tests/application/fakes.py` as the file imports today; `RecordingLogScope` from `tests/fakes/observability.py`):
- `test_a_claimed_job_runs_inside_its_delivery_log_scope` — a handler that asserts
  `scope.active` during `handle`; afterwards `scope.bound_ids == [str(DELIVERY_CORRELATION.for_project(project_id).value)]`.
- `test_nothing_claimable_enters_no_scope` — empty queue → `scope.bound_ids == []`.
- `test_a_handler_exception_still_leaves_the_scope` — handler raises; the job is nacked as today and
  `scope.active` is False afterwards.
Append to `tests/infrastructure/test_correlation_log_context.py`:
- `test_the_real_scope_binds_structlog_contextvars_for_a_worker_job` — `WorkerLoop(..., log_scope=CorrelationLogContext())`
  with the fakes above and a handler that captures `structlog.contextvars.get_contextvars()`; the
  captured `correlation_id` equals the derived id, and after `run_once` `CORRELATION_LOG_FIELD` is
  absent from `get_contextvars()`.
- `test_the_log_context_satisfies_the_application_port` — `isinstance(CorrelationLogContext(), LogCorrelationScope)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_worker.py tests/infrastructure/test_correlation_log_context.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The DESIGN spend correlation (`roadmap-89-design-spend-correlation`); log lines outside a job.
- vibey_bootstrap's `correlation_scope` (the class docstring gives the reason it is not used).
- Roles, audit, identity (#89 children 3–8, blocked). Docs, CHANGELOG. Do not push; commit locally
  with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
