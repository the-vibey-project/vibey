## Title
feat(worker): the running job is a declared, ambient scope that anything the handler awaits can read

## Why
A routed sovereign answer must be recorded in the ledger against the job that asked for it
(7.c, `src/vibey_tools/gh/docs/doctrines.md:82`; lane `gap-design-via-sovereignloop-4`). The
ledger needs `project_id`, `cycle`, `phase` and `job_id`, but the sovereign providers are
called without the job: `DesignInterviewHandler.handle` calls
`self._questions.batch(stage, events)` (`src/vibey/application/design_handler.py:53`), and the
chat client beneath the provider sees only prompts. Threading a job parameter through every
provider, handler and chat call would touch a dozen signatures for one fact.

The codebase already says where this belongs: `CorrelationLogContext`'s docstring
(`src/vibey/infrastructure/logging.py:170-181`) records that "the scope belongs at the job
execution boundary in `WorkerLoop` ... wiring it needs an application-side port and a binding
in the composition root, and that is its own change". This lane is that port and that
binding, held in a `ContextVar` so it survives `await` and never leaks between concurrent
jobs. It is declared (9.b, `doctrines.md:349`): a class, an interface beside it, and the
worker taking it by keyword with a production default.

## Required behaviour
1. New `src/vibey/application/job_scope.py` (provenance line 1, copied from
   `src/vibey/application/worker.py:1`) holds `class JobScope`:
   - `__init__(self) -> None` creates one `contextvars.ContextVar[JobRecord | None]` named
     `"vibey_running_job"` with `default=None`, per instance, so two scopes never see each
     other's jobs (the comment says so).
   - `current(self) -> JobRecord | None`: the job bound in this context, or `None`.
   - `bound(self, job: JobRecord) -> contextlib.AbstractContextManager[JobRecord]`, built with
     `@contextlib.contextmanager`: sets the variable, yields `job`, and in `finally` resets it
     with the token, so a nested scope restores the outer job and an exception restores it too.
   - Module constant `JOB_SCOPE: Final[JobScopeInterface] = JobScope()`, the one production
     scope (the comment says: the worker and the recorder must share one instance, and this is it).
2. New `src/vibey/application/interfaces/job_scope_interface.py` (provenance line 1) declares
   `@runtime_checkable class JobScopeInterface(Protocol)` with `current` and `bound`, same
   signatures, docstrings only. It imports `JobRecord` from `vibey.application.dto` under
   `TYPE_CHECKING` only if a cycle appears; otherwise directly.
3. `WorkerLoop.__init__` (`src/vibey/application/worker.py:61-77`) gains the keyword
   `scope: JobScopeInterface | None = None`, placed after `telemetry_enabled`, stored as
   `self._scope = scope if scope is not None else JOB_SCOPE`.
4. In `WorkerLoop.run_once`, the handler call (`worker.py:157-158`) becomes:
   ```python
                try:
                    with self._scope.bound(job):
                        outcome = await self._handler.handle(job)
                except CapacityDeferred as exc:
   ```
   Nothing else in `run_once` changes: settling, the heartbeat, spans and metrics run outside
   the scope exactly as before.
5. `tests/fakes/registry.py` (lane `fakes-registry`) gains
   `EXEMPT[JobScopeInterface] = ExemptReason.PURE_POLICY`: the real `JobScope` does no I/O, so
   tests use it.

## Where to change
- New `src/vibey/application/job_scope.py`, `src/vibey/application/interfaces/job_scope_interface.py`.
- `src/vibey/application/worker.py`: two edits with edit_file (the constructor and the
  handler call). The file is 450+ lines: never write_file.
- `tests/fakes/registry.py`: one EXEMPT entry (edit_file).
- New `tests/application/test_job_scope.py`.
- Pattern for the worker test: `tests/application/test_worker.py:131-140`
  (`FakeJobRepository`, `FakeHumanGateRepository`, `make_job`, `run_once(PROJECT_ID)`).

## Acceptance criteria
- [ ] Every test in `tests/application/test_worker.py` passes unchanged.
- [ ] `WorkerLoop(...)` built without `scope` binds `JOB_SCOPE`.
- [ ] `tests/fakes/test_port_parity.py` passes with the new EXEMPT entry.
- [ ] 100% branch coverage of `src/vibey/application/*`.

## Tests to write first (TDD)
`tests/application/test_job_scope.py`:
- `test_nothing_is_bound_outside_a_job` -- a fresh `JobScope().current()` is `None`.
- `test_bound_exposes_the_job_and_nesting_restores_the_outer_one` -- inside `bound(a)`, `current()` is `a`; inside a nested `bound(b)` it is `b`; after the inner block it is `a`; after both, `None`.
- `test_bound_restores_after_an_exception` -- a `ValueError` raised inside the block propagates, and `current()` is `None` afterwards.
- `test_the_job_survives_awaits_and_reaches_tasks_created_inside` -- inside `bound(a)`, after `await asyncio.sleep(0)` and inside `asyncio.create_task(...)`, `current()` is `a`.
- `test_concurrent_jobs_each_see_their_own` -- `asyncio.gather` over two coroutines, each binding its own job and awaiting `asyncio.sleep(0)` before reading `current()`, returns `(a, b)`.
- `test_two_scopes_never_share_a_job` -- binding one `JobScope` leaves another's `current()` at `None`.
- `test_the_worker_binds_the_running_job_for_its_handler` -- a handler class whose `handle` stores `scope.current()` and returns `Success()`; `WorkerLoop(jobs=FakeJobRepository([job]), gates=FakeHumanGateRepository(), handler=handler, owner="w1", scope=scope)`; after `await loop.run_once(PROJECT_ID)` the handler saw `job` and `scope.current()` is `None` again.
- `test_the_worker_defaults_to_the_production_scope` -- the same run without `scope=` lets the handler read the job from `JOB_SCOPE.current()`.
- `test_scope_satisfies_its_interface`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Binding the scope for log correlation (`CorrelationLogContext`): a separate change.
- The ledger recorder that reads the scope (`gap-design-via-sovereignloop-4`).
- `bootstrap.py`: every `WorkerLoop(` (`bootstrap.py:215`, `:247`, `:626`) keeps its call; the
  default scope is the production one.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(worker): the running job is a declared, ambient scope`. Do not push.

## Lane card
- **Depends on:** `fakes-registry`.
- **Must keep passing unchanged:** `tests/application/test_worker.py`, `tests/test_bootstrap.py`,
  every protected test.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
