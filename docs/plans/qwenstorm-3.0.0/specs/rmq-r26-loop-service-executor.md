## Title
feat(loop-service): DESIGN and DECOMPOSE runs go through the loop service too

## Why
ADR-0044 §13. The DESIGN and DECOMPOSE providers do not use `EngineAdapter`. They
spawn through an injected `CommandExecutor` that returns `CommandResult(returncode, stdout, stderr)`
(`claudeloop_process.py:28-47` and `:88-104`, `opencodeloop_process.py:26-45` and
`:79-85`).

"Callers publish run jobs instead of spawning runner subprocesses" covers these runs
as well. A service-backed `CommandExecutor` keeps both providers unchanged.

## Required behaviour
1. `class LoopServiceCommandExecutor(engine_id: str, binary: str, client: LoopServiceClientInterface, *, clock, run_queue_wait: timedelta, deadline: timedelta)`
   implements `vibey.infrastructure.interfaces.CommandExecutor`.
2. `async def execute(self, argv: tuple[str, ...]) -> CommandResult`:
   - `argv[0]`'s basename must equal `binary`, else `ValueError`.
   - The run id is the value after `--run-id` in `argv`, else a new `uuid4`.
   - The cwd is the value after `--cwd`, else `ValueError("the loop service needs --cwd in argv")`.
   - Submit `RunRequest(purpose=RUN, args=argv[1:], cwd=…, run_dir=None, supersedes=None, capture_output=True, start_by=now+run_queue_wait, deadline_seconds=…)`.
   - An unaccepted request, or a result `REJECTED` for `worktree busy` or lateness,
     raises `EngineQueueSaturated` (R25).
   - Otherwise return `CommandResult(result.exit_code if it is not None else 1, result.stdout or "", result.stderr or "")`.
3. Capacity detection stays where it is today, in each provider's own parsing of the
   run directory and stderr (`claudeloop_process.py:148-172`). The executor adds none.

## Where to change
- The new module and its interface. The `CommandExecutor` Protocol is in
  `src/vibey/infrastructure/interfaces/`.

## Acceptance criteria
- [ ] With the in-memory client and a stub responder, `ClaudeLoopProcess(executor=LoopServiceCommandExecutor(...))` produces the same `ClaudeLoopResult` as it does with `AsyncSubprocessExecutor`, for the same scripted run directory and stderr.
- [ ] A missing `--cwd` or a wrong binary raises.
- [ ] Saturation raises `EngineQueueSaturated`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_command_executor.py`:
  - `test_execute_round_trips_returncode_stdout_stderr`
  - `test_claudeloop_process_runs_unchanged_over_the_service`
  - `test_opencodeloop_process_runs_unchanged_over_the_service`
  - `test_missing_cwd_and_wrong_binary_raise`
  - `test_saturation_raises`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines tests/cli/test_sovereign_provider_options.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Selecting this executor in the CLI (R28).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R24, and R25 (for `EngineQueueSaturated`).
- **Wave:** 5.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/command_executor.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/command_executor_interface.py` (new)
  - `tests/infrastructure/loop_service/test_command_executor.py` (new)
- **Parallel-safe with:** R13, R14 and R23.
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/test_claudeloop_process.py`
  - `tests/infrastructure/engines/test_opencodeloop_process.py`
  - `tests/cli/test_sovereign_provider_options.py`
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
