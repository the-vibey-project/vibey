## Title
refactor(engines): extract the run-directory tailer, the inbox writer and the process launcher from LoopProcessAdapter

## Why
ADR-0044 §13. The loop service (R21, R22) and the caller-side `LoopServiceAdapter`
(R25) need exactly the machinery `LoopProcessAdapter` already has:

- launching an engine with the orchestrator's Python environment stripped and the
  local overlay applied (`loop_process_adapter.py:87-111`, `:160-192`, `:357-359`);
- tailing `events.jsonl` into `EngineEvent`s (`:418-589`);
- writing inbox commands (`:591-614`, `:653-657`);
- reading `stop-summary.md` (`:659-682`).

Duplicating it would break sub-doctrine 10.e inside this very repository. This lane
extracts those pieces into classes behind interfaces (9.b), and **the adapter's
behaviour does not change**.

## Required behaviour
1. `run_dir.py`:
   - `class RunDirTailer(descriptor: EngineDescriptor)`, with the method
     `async def tail(self, run_dir: Path, *, run_id: object, process_exited: Callable[[], bool]) -> AsyncIterator[EngineEvent]`.
     It is the body of `LoopProcessAdapter.tail` (`:425-589`) moved verbatim. The
     `_active_processes` exit check (`:567-580`) becomes the injected
     `process_exited()`, with the same one-poll grace.
   - `class RunInbox(run_dir: Path)`, with `write_prompt(text: str, *, now: bool) -> Path`
     (the body of `:593-614`), `write_stop() -> Path` (`:654-657`) and
     `write_command(command: str) -> Path`.
   - `class StopSummaryReader(descriptor)`, with
     `async def read(self, run_dir: Path, *, wait_seconds: float = 30.0) -> tuple[str, bool]`.
     It waits for the summary and returns `(summary, complete)`, with the logic of
     `:659-673`.
2. `process_launcher.py`: `class EngineProcessLauncher(descriptor, *, env_overlay, python_env)`
   with three methods:
   - `environment() -> dict[str, str]` (from `_engine_environment`, `:160-164`)
   - `async def spawn(self, *argv, env=None, stdout, stderr, cwd=None, start_new_session=False)`
     (from `_spawn`, `:166-192`)
   - `resolve(argv) -> tuple[str, ...]` (from `:357-359`)

   It calls `asyncio.create_subprocess_exec` and `shutil.which` **through the module
   attributes** (`asyncio.create_subprocess_exec(...)`, `shutil.which(...)`), never
   through `from asyncio import …`. That way the existing tests' monkeypatches of those
   globals still reach it.
3. `LoopProcessAdapter` delegates to these classes. `_active_processes`,
   `_diagnostic_files`, `_help_text_cache`, `isolate_python_env`, `ProcessError`,
   `_render_plan` and every public method **stay in `loop_process_adapter.py`**, with
   the same names and signatures. `__all__` is unchanged.
4. Behaviour is byte-identical: the same log event names, the same argv, the same
   environment, the same timeouts.

## Where to change
- `src/vibey/infrastructure/engines/loop_process_adapter.py` and the two new modules.
- The interfaces go in `infrastructure/engines/interfaces/`, a package already listed
  in `.importlinter:98-120`.

## Acceptance criteria
- [ ] `tests/infrastructure/engines/test_loop_process_adapter.py` passes **with no edits**.
- [ ] The live, protected and conformance tests pass.
- [ ] The new classes have direct unit tests.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/engines/test_run_dir.py`:
  - `test_tailer_translates_and_stops_on_terminal_meta`
  - `test_tailer_stops_after_process_exits_without_status`
  - `test_inbox_writes_prompt_stop_and_command_files`
  - `test_stop_summary_reader_waits_and_detects_the_marker`
- `tests/infrastructure/engines/test_process_launcher.py`:
  - `test_environment_strips_the_orchestrator_venv_and_applies_the_overlay`
  - `test_resolve_uses_an_absolute_binary_path`
  - `test_spawn_merges_the_overlay_last`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/test_gate_runner.py tests/infrastructure/process tests/application/test_conformance.py tests/system/test_full_worker_faked.py tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/infrastructure/engines/test_loop_process_adapter.py tests/live

## Out of scope
- Any service or queue code.
- Changing any behaviour.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/infrastructure/engines/run_dir.py` (new)
  - `src/vibey/infrastructure/engines/process_launcher.py` (new)
  - `src/vibey/infrastructure/engines/interfaces/{run_dir_interface,process_launcher_interface}.py` (new)
  - `src/vibey/infrastructure/engines/loop_process_adapter.py`
  - `tests/infrastructure/engines/{test_run_dir,test_process_launcher}.py` (new)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/test_loop_process_adapter.py`, all of it. It imports
    `_active_processes` and `_diagnostic_files` from the adapter module (`:23-24`), and
    it monkeypatches `module.asyncio.create_subprocess_exec` and `module.shutil.which`
    (`:1565-1566`).
  - `tests/infrastructure/test_gate_runner.py` and `tests/infrastructure/process/test_call_sites.py`,
    since `infrastructure/build/gate_runner.py:45` imports `isolate_python_env` from
    the adapter module.
  - `tests/application/test_conformance.py`
  - `tests/system/test_full_worker_faked.py`
  - `tests/live/**` (protected)
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
