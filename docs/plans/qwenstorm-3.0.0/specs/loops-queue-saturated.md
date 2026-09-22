## Title
feat(worker): a saturated loop queue defers without capacity (EngineQueueSaturated), and every run carries its job's supersede identity

ADR-0046 lane L15 (slug `loops-queue-saturated`).

## Why
Draft ADR-0046 §5 (`specs/ADR-two-loops.md:232`), the "queue saturation" row: "no `RunAccepted`
by `start_by` … `EngineQueueSaturated` becomes `Defer(capacity=False)`. No circuit opens, no
attempt is spent, and it **never** triggers a paid fallback: busy is not 'cannot carry' (8.a)".
§3's idempotency table (`:190`) fences run ownership by `supersedes {key: job_id, attempt}`, so a
run must know its job. §10 (`:303`) puts `EngineQueueSaturated` in `application/worker.py`. The
superseded R25 (`issue-audit/updates/372.md`, "Carried over into ADR-0046") carries three
behaviours here verbatim; `specs/rmq-r25-loop-service-adapter.md` behaviours 1–3 are their text.

At integration `d3b4a388`: `RunSpec` (`src/vibey/application/dto.py:109-119`) has no job identity;
`BuildImplementHandler` builds it at `src/vibey/application/build_implement_handler.py:222-231`;
and `WorkerLoop.run_once` (`src/vibey/application/worker.py:130-178`) knows one deferral
exception, `CapacityDeferred` (`:46-57`, caught at `:159-165` as `Defer(capacity=True)`), which
`RotationRecordingHandler` would record as a capacity rejection and open the circuit
(`src/vibey/application/engine_selection.py:371-389`). A busy queue must never look like that.

## Required behaviour
1. `RunSpec` gains two fields **at the end**, after `session_id`, so every existing constructor
   call still works:
   ```python
       supersede_key: str | None = None
       """The run's supersede key: its job id (ADR-0046 §6). A later attempt of the same key
       stops a lower one, across both loops."""
       attempt: int = 0
       """The job's attempt number for this run; with `supersede_key`, the fence's high-water mark."""
   ```
2. `BuildImplementHandler` passes `supersede_key=str(job.id)` and `attempt=job.attempts` in the
   `RunSpec(...)` it builds at `:224-230` (after `isolation=IsolationLevel.WORKTREE,`).
3. `application/worker.py` adds, directly after `CapacityDeferred` (`:46-57`):
   ```python
   class EngineQueueSaturated(Exception):
       """A loop's queue did not take a run in time (ADR-0046 §5): busy, not out of capacity.

       The worker defers the job with `capacity=False`: no circuit opens, no attempt is spent,
       and it never becomes a paid fallback -- busy is not "cannot carry" (sub-doctrine 8.a).
       """

       def __init__(self, retry_at: datetime, detail: str) -> None:
           super().__init__(detail)
           self.retry_at = retry_at
           self.detail = detail
   ```
   and `run_once` catches it right after the `except CapacityDeferred as exc:` clause
   (`:159-165`), before the generic `except Exception`. The `except` keyword sits at exactly the
   indentation of `except CapacityDeferred as exc:` (16 spaces), its body at 20:
   ```python
                except EngineQueueSaturated as exc:
                    # Busy is not a capacity signal (ADR-0046 §5): no circuit, no attempt.
                    outcome = Defer(exc.retry_at, exc.detail, capacity=False)
   ```
   `"EngineQueueSaturated"` is not added to `__all__` (`CapacityDeferred` is not in it either;
   both are imported by name).
4. Consequences, all through existing code: the job returns to READY with `run_after = retry_at`
   and its attempt count restored (`FakeJobRepository.defer`, `tests/application/fakes.py:155-176`,
   mirrors the real one); the `job.deferred` line is logged at INFO with `capacity=False`
   (`worker.py:213-223`); `RotationRecordingHandler` sees an exception, not a capacity `Defer`,
   so it records nothing and the engine's circuit stays as it was.

**Stop rule.** If an existing test compares whole `RunSpec` values and fails because of the two
new fields, stop and report its path and line: do not edit it.

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first. All three files are
over 100 lines: `edit_file` only.
- `src/vibey/application/dto.py`: the two fields after the unique line
  `    session_id: str | None = None  # set to resume a warm session`.
- `src/vibey/application/build_implement_handler.py`: in the `RunSpec(` call, after the unique
  line `                isolation=IsolationLevel.WORKTREE,` add
  `                supersede_key=str(job.id),` and `                attempt=job.attempts,`.
- `src/vibey/application/worker.py`: the class after `CapacityDeferred` and the `except` clause
  of behaviour 3 (anchor: the unique text
  `                        capacity_state=exc.capacity_state,\n                    )` that closes
  the `CapacityDeferred` handler).
- New test file `tests/application/test_queue_saturation.py` (line 1: the provenance comment
  copied from `tests/application/test_worker.py`).

## Acceptance criteria
- [ ] Every test below passes; `tests/application/test_worker.py`,
      `tests/application/test_build_implement_handler.py` and every `tests/infrastructure/engines`
      test that builds a `RunSpec` pass unedited.
- [ ] `grep -n "class EngineQueueSaturated" src/vibey/application/worker.py` prints one line.
- [ ] `src/vibey/application/*` stays at 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_queue_saturation.py`. Seams only: `FakeJobRepository`,
`FakeHumanGateRepository` and `make_job` (`tests.fakes.queue`); `InMemoryWorktrees` and
`RecordingProvisioner` (`tests.fakes.build`, lane `fakes-build`; read their constructors first);
`build_ledger(InMemoryLedger())` (`tests.fakes.ledger`); `ScriptedEngine` with the `CLAUDELOOP`
descriptor; `EngineHealthService(FakeEngineHealthRepository())` (`tests.fakes.engines`).
- `test_run_spec_gains_supersede_key_and_attempt_with_defaults`: a `RunSpec` built with the five
  required fields has `supersede_key is None` and `attempt == 0`; built with
  `supersede_key="k", attempt=3` it keeps both; a positional call with six arguments
  (`session_id` sixth) still works.
- `test_the_handler_passes_the_job_identity_to_the_run`: a `ScriptedEngine` subclass whose
  `start` records `spec` before `super().start(spec)` (as `_PromptCapturingEngine` does,
  `tests/application/test_build_implement_handler.py:548-553`); a `build.implement` job with
  `attempts=2` → the recorded spec has `supersede_key == str(job.id)` and `attempt == 2`.
- `test_engine_queue_saturated_carries_its_retry_time_and_detail`: `exc.retry_at`,
  `exc.detail`, and `str(exc) == detail`.
- `test_queue_saturation_defers_without_capacity_and_spends_no_attempt`: a `WorkerLoop` whose
  handler raises `EngineQueueSaturated(retry_at, "no sovereignloop router answered within 30s")`
  on a job with `attempts=2` → after `run_once`, the job is `JobState.READY`, `attempts == 2`,
  `run_after == retry_at`, and the logger line is `("info", "job.deferred", ...)` with
  `capacity=False` (import `_RecordingLogger` from `tests.application.test_worker`, `:639-659`,
  or the shared recording logger of lane `fakes-observability` if it exists).
- `test_queue_saturation_opens_no_circuit`: the same, with the handler wrapped in
  `RotationRecordingHandler(inner=<raising handler>, health=health, project_id=PROJECT_ID, engine_id=EngineId.CLAUDELOOP)`
  → `await health.list_for_project(PROJECT_ID) == ()` (nothing was recorded against the engine).
- `test_capacity_deferred_is_still_a_capacity_defer`: `CapacityDeferred(retry_at, "window")` →
  the logger line is at `warning` with `capacity=True` (the new clause did not swallow it).

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/application tests/application/test_queue_saturation.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_queue_saturation.py tests/application/test_worker.py tests/application/test_build_implement_handler.py tests/application/test_engine_selection.py tests/infrastructure/engines tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    git diff --stat HEAD -- tests/application/test_worker.py tests/application/test_build_implement_handler.py
    git diff --stat

## Out of scope
- Who raises `EngineQueueSaturated` (lanes `loops-selecting-loop-provider`,
  `loops-service-adapter-run`, `loops-command-executor`) and the worktree fence that reads the
  supersede key (lane `loops-worktree-fence`).
- `LoopProcessAdapter` and the other adapters: they ignore the new fields.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `fakes-build`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
