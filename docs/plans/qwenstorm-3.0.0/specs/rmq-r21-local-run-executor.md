## Title
feat(loop-service): run one request as a local engine subprocess and persist its result

## Why
ADR-0044 §13. The loop service runs each request **as the runner's own CLI in a
subprocess**, with the same argv, run directory, inbox and exit codes as today. The
protected live conformance suite therefore keeps pinning what runs.

The service also persists each result beside the diagnostics `LoopProcessAdapter`
already writes (`loop_process_adapter.py:365-368`), before it acknowledges the
request. That is what makes a redelivered request idempotent.

It must run only its own binary, only under a configured root, and with only the
arguments `RunArgsPolicy` allows (R19). This is the security boundary the ADR names.

## Required behaviour
1. `class RunResultStore`:
   - `path(cwd: str, run_id: UUID) -> Path` returns
     `Path(cwd)/.vibey/diagnostics/<run_id>.result.json`.
   - `write(cwd, result: RunResult) -> None` writes atomically (a temp file plus
     `os.replace`) using `RunProtocolCodec`.
   - `read(cwd, run_id) -> RunResult | None` returns `None` when the file is missing,
     and `None` with a `warning` log when it is malformed.
2. `class LocalRunExecutor(binary: str, launcher: EngineProcessLauncherInterface, reaper: ProcessReaperInterface, root: Path)`:
   - `reason_to_reject(request: RunRequest) -> str | None` combines
     `RunArgsPolicy.reason`, `cwd` being absolute and `Path(cwd).resolve()` lying under
     `root.resolve()`, and `run_dir` (when given) lying under `cwd`.
   - `async def start(self, request) -> LocalRunInterface`:
     - Resolve `(binary, *request.args)` through the launcher.
     - For `purpose=RUN` without `capture_output`, stdout and stderr go to
       `<cwd>/.vibey/diagnostics/<run_id>.stdout` and `.stderr`. Otherwise they are
       pipes, keeping the last 64 KiB of each.
     - Spawn with `cwd=request.cwd` and `start_new_session=True`.
3. `class LocalRun`:
   - `pid`
   - `async def wait(self, timeout: float | None) -> int | None`: the exit code, or
     `None` on a timeout
   - `async def stop(self, grace_seconds: float) -> None`: when there is a `run_dir`,
     call `RunInbox(run_dir).write_stop()`; wait `grace_seconds`; if the process is
     still alive, call `reaper.kill_and_reap(process)`
   - `control(command: RunControlCommand, text: str | None) -> None`: map
     `STOP`/`WIND_DOWN` to `RunInbox.write_command(command.value)` and the two prompt
     commands to `write_prompt`
   - `output() -> tuple[str | None, str | None]`
   - `meta_status() -> str | None`: `run_dir/meta.json`'s `status`, or `None`
4. `.importlinter`: `vibey.infrastructure.loop_service.interfaces` joins the
   `infrastructure-interfaces-declare-only` contract's `source_modules`.

## Where to change
- The new package. Use R20's `EngineProcessLauncher` and `RunInbox`, and the existing
  `ProcessReaper` (`infrastructure/process/reaper.py`).

## Acceptance criteria
- [ ] A scripted fake engine is written into a temp directory on `PATH`, like the
  existing adapter tests (`test_loop_process_adapter.py:389-420`). It runs, its exit
  code comes back, its stdout lands in the diagnostics file, and `meta_status` reads
  its `meta.json`.
- [ ] `stop` writes the inbox stop and kills the process after the grace period.
- [ ] Each rejection reason fires: arguments, a `cwd` outside the root, a relative
  `cwd`, and a `run_dir` outside `cwd`.
- [ ] The result store round-trips, writes atomically, and returns `None` for a
  missing or malformed file.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_local_run_executor.py`:
  - `test_runs_the_fake_engine_and_returns_its_exit_code`
  - `test_run_output_goes_to_the_diagnostics_files`
  - `test_probe_output_is_captured_and_capped`
  - `test_stop_writes_the_inbox_then_kills_after_grace`
  - `test_control_maps_commands_to_inbox_files`
  - `test_rejects_each_unsafe_request`
- `tests/infrastructure/loop_service/test_result_store.py`:
  - `test_round_trip`
  - `test_write_is_atomic`
  - `test_missing_and_malformed_read_none`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines tests/meta/test_import_contracts_bind.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- AMQP (R22–R24).
- CLI (R27).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R19, R20.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/__init__.py` (new)
  - `src/vibey/infrastructure/loop_service/{local_run_executor,result_store}.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/{__init__,local_run_executor_interface,result_store_interface}.py` (new)
  - `.importlinter`
  - `tests/infrastructure/loop_service/{__init__,test_local_run_executor,test_result_store}.py` (new)
- **Parallel-safe with:** R04, R07, R10 and R29. It precedes R12 in the `.importlinter` chain.
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/*`
  - `tests/infrastructure/process/*`
  - `tests/meta/test_import_contracts_bind.py`
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
