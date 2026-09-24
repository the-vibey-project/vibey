## Title
feat(engines): LoopServiceAdapter publishes a run instead of spawning one

## Why
ADR-0044 §13. The engine seam `EngineAdapter` (`application/interfaces/engines.py:44-80`)
does not change. A second implementation publishes to the engine's loop service.

Its evidence path stays exactly today's: it tails `events.jsonl` on the shared volume
through R20's `RunDirTailer`. So `run_and_record` (`build_engine_run.py:70-159`) and
the order it checks capacity before completion (`build_implement_handler.py:241-263`)
are untouched.

Two new facts need small application changes:

- **A run's supersede identity comes from its job.** `RunSpec` gains `supersede_key`
  and `attempt`.
- **A saturated engine queue is not an engine capacity signal.** It must defer
  without opening a circuit (`application/interfaces/queue.py:40-57`), so the worker
  gets an `EngineQueueSaturated` beside `CapacityDeferred` (`worker.py:46-57`,
  `:159-165`).

## Required behaviour
1. `RunSpec` (`application/dto.py:110-119`) gains `supersede_key: str | None = None`
   and `attempt: int = 0`, both at the end, so every existing constructor call still
   works.
2. `build_implement_handler.py:222-230` passes `supersede_key=str(job.id)` and
   `attempt=job.attempts`.
3. `application/worker.py` adds `class EngineQueueSaturated(Exception)` with
   `retry_at` and `detail`. `run_once` catches it beside `CapacityDeferred` and
   produces `Defer(exc.retry_at, exc.detail, capacity=False)`.
4. `class LoopServiceAdapter(descriptor: EngineDescriptor, client: LoopServiceClientInterface, *, clock, run_queue_wait: timedelta, deadline: timedelta, root_hint: str | None = None)`
   implements `EngineAdapter`:
   - **`start(spec)`:**
     - Write the plan to `spec.worktree_path/.vibey/plans/<run_id>.md`, using
       `_render_plan` exactly as `loop_process_adapter.py:341-346` does.
     - Set `args = build_argv(descriptor, spec)[1:]` (`argv.py:10-30`) and
       `run_dir = worktree/<state_dir>/runs/<run_id>`.
     - Submit a `RunRequest(purpose=RUN, cwd=str(worktree_path), supersedes=RunSupersede(spec.supersede_key, spec.attempt) if spec.supersede_key else None, start_by=now+run_queue_wait, deadline_seconds=deadline, capture_output=False, …)`.
     - Await `ticket.accepted(run_queue_wait + 5 s)`. If it is `None`, or the result
       is `REJECTED` with `"worktree busy"` or `"not started before start_by"`, raise
       `EngineQueueSaturated(retry_at=now+run_queue_wait, detail=...)`.
     - Otherwise return `RunHandle(run_id, engine_id, run_dir, pid=accepted.pid)`.
   - **`tail(handle)`:** `RunDirTailer.tail(run_dir, run_id=…, process_exited=lambda: ticket.latest_result is not None)`.
   - **`run_exit_code(handle)`:** `ticket.latest_result.exit_code`, else
     `RunResultStore.read(cwd, run_id).exit_code`, else `None`.
   - **`diagnostic_tail(handle)`:** the tail of the diagnostics stdout and stderr
     files, as `loop_process_adapter.py:625-642` does. `release_diagnostics` is a
     no-op.
   - **`send_prompt`:** publishes `RunControl(PROMPT_NOW or PROMPT_AT_BREAK)`.
   - **`stop(handle)`:** publishes `RunControl(STOP)`, then builds `StopSummary` from
     `StopSummaryReader` and `snapshot()` as `:659-706` does, with no process
     handling.
   - **`snapshot`:** as in `:708-727`.
   - **`preflight()`:** probes `("--version",)` and `("doctor", *descriptor.doctor_args)`,
     and caches `("run", "--help")` output for `help_text`, all through
     `client.probe(timeout=descriptor-appropriate: 10 s, doctor 120 s)`. A probe with
     no answer gives `PreflightResult(installed=False, …, detail="no loop service answered for <engine>")`.
   - **`help_text`:** a sync property returning the cached text, or `None` before the
     first `preflight()`.
   - **`classify` and `attribute`:** from `classify.py`, unchanged.

## Where to change
- The new module, plus the three application files named on the card.

## Acceptance criteria
- [ ] Every scenario uses the in-memory client and R24's stub responder, which writes `events.jsonl` and `meta.json` into a temp worktree.
- [ ] `run_and_record` sees the same events and exit code as it would from a subprocess.
- [ ] Exit 75 reaches the wind-down path.
- [ ] A capacity-rejection event still outranks a completion verdict.
- [ ] Queue saturation becomes `Defer(capacity=False)` in `WorkerLoop`, and no circuit opens.
- [ ] Preflight and `help_text` come from probes.
- [ ] No existing test needed an edit.
- [ ] 100% coverage on `application/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_adapter.py`:
  - `test_start_writes_the_plan_and_submits_the_same_argv`
  - `test_tail_reads_run_dir_events_until_the_result`
  - `test_exit_code_from_the_result_or_the_persisted_file`
  - `test_wind_down_exit_75_reaches_the_handler`
  - `test_capacity_event_outranks_completion`
  - `test_unaccepted_run_raises_queue_saturated`
  - `test_busy_worktree_raises_queue_saturated`
  - `test_stop_sends_control_and_reads_the_summary`
  - `test_preflight_and_help_text_come_from_probes`
  - `test_adapter_satisfies_engine_adapter`
- `tests/application/test_worker.py`: `test_queue_saturation_defers_without_capacity`
- `tests/application/test_build_implement_handler.py`: `test_run_spec_carries_job_identity`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/application tests/fakes tests/system tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Selecting this adapter (R28).
- The DESIGN executor (R26).
- Docs and CHANGELOG.

**Stop rule:** if an existing test compares whole `RunSpec` values and fails because
of the new fields, stop and report.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R20, R24.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/adapter.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/adapter_interface.py` (new)
  - `src/vibey/application/dto.py` (`RunSpec`: two defaulted fields)
  - `src/vibey/application/worker.py` (one new exception, caught beside `CapacityDeferred`)
  - `src/vibey/application/build_implement_handler.py` (`:222-230`: pass the two fields)
  - `tests/infrastructure/loop_service/test_adapter.py` (new)
  - `tests/application/test_worker.py` (new test only)
  - `tests/application/test_build_implement_handler.py` (new test only)
- **Parallel-safe with:** R13, R14, R23 and R26. Note that R26 also imports the new exception.
- **Must keep passing unchanged:**
  - every existing test in `tests/application/test_worker.py` and `tests/application/test_build_implement_handler.py`
  - `tests/fakes/test_port_parity.py`
  - `tests/system/*`
  - `tests/live/**`
  - all protected tests
- **Standing constraints:** see the header list.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
