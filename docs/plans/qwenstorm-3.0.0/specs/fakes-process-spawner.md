## Title
test(fakes): the loop process adapter spawns through a declared seam, and a scripted process fake replaces 33 patches

## Why
`LoopProcessAdapter` (`src/vibey/infrastructure/engines/loop_process_adapter.py:115-738`) is
how vibey runs every engine. Its test module (`tests/infrastructure/engines/test_loop_process_adapter.py`,
1,971 lines) reaches the adapter's covered branches only by patching, 33 times in all:
- `asyncio.create_subprocess_exec` on the module (`:1565`, `:1607`, `:1679`, `:1922`);
- `shutil.which` (`:1566`, `:1608`);
- `subprocess.run` (`:382`, `:419`);
- `asyncio.wait_for`, 5 times (`:737`, `:769`, `:940`, `:997`, `:1173`), to fake a process
  that never exits;
- `sys.prefix` (`:1943-1963`).

The adapter already has two injected collaborators (`python_env`, `_reaper`). It spawns
directly in `_spawn` (`:173-192`), looks binaries up with `shutil.which` (`:228`, `:269`,
`:357`), probes versions with `subprocess.run` (`:247`), and hard-codes the stop timeouts
2.0 and 1.0 (`:690`, `:694`).

## Required behaviour
0. **Lane `split-367-2-process-launcher` lands first and owns the spawner seam.** It declares
   `ProcessSpawnerInterface` and `ExecutableResolverInterface` in
   `src/vibey/infrastructure/engines/interfaces/process_launcher_interface.py`, the production
   `AsyncioProcessSpawner`, and gives `LoopProcessAdapter` the fields `spawner` and `resolver`.
   Preflight: `grep -n "class ProcessSpawnerInterface" src/vibey/infrastructure/engines/interfaces/process_launcher_interface.py`
   must print one line; if it does not, stop and report instead of declaring a second one. So:
   - item 1 below does **not** declare another `ProcessSpawnerInterface`: it declares
     `SpawnedProcessInterface` in `process_interface.py` and narrows the return type of 367-2's
     `ProcessSpawnerInterface.spawn` from `asyncio.subprocess.Process` to
     `SpawnedProcessInterface` (which `asyncio.subprocess.Process` satisfies), so a
     `ScriptedProcess` can stand in; `ASYNCIO_SPAWNER` is an `AsyncioProcessSpawner()` instance;
   - item 2 does **not** add `spawner` or `locator`: 367-2's `spawner` and `resolver` are those
     seams, and the three `shutil.which` calls become `self.resolver.which` (the same shape as
     `fakes-process-executor`'s `ExecutableLocator`, so one fake serves both). Item 2 adds only
     `runner`, `stop_wait_seconds` and `stop_terminate_seconds`;
   - `tests/fakes/process.py` may already exist (from `fakes-process-executor` or 367-2's tests):
     append to it with `edit_file`, never rewrite it.
1. **`ProcessSpawnerInterface`** (in `src/vibey/infrastructure/interfaces/process_interface.py`,
   beside `fakes-process-executor`'s seams):
   `async def spawn(self, argv: Sequence[str], *, env: Mapping[str, str] | None, stdout: int | TextIO, stderr: int | TextIO, cwd: Path | None, start_new_session: bool) -> SpawnedProcessInterface`.
   - `SpawnedProcessInterface` is the part of `asyncio.subprocess.Process` the adapter uses:
     `pid`, `returncode`, `stdout`, `stderr`, `wait()`, `communicate()`, `terminate()` and `kill()`.
   - The production `ASYNCIO_SPAWNER: Final` calls `asyncio.create_subprocess_exec`, with the
     arguments `_spawn` passes today.
   - Add it to `DRIVER_SEAMS`.
2. **New dataclass fields on `LoopProcessAdapter`**, each with a production default:
   - `spawner: ProcessSpawnerInterface = ASYNCIO_SPAWNER`;
   - `locator: ExecutableLocator = PATH_LOCATOR`;
   - `runner: SyncCommandRunner = SUBPROCESS_RUNNER`;
   - `stop_wait_seconds: float = 2.0`;
   - `stop_terminate_seconds: float = 1.0`.
   `_spawn` merges the environment exactly as it does now, then calls `self.spawner.spawn(...)`.
   The three `shutil.which` calls become `self.locator.which`, `subprocess.run` becomes
   `self.runner.run`, and `:690` and `:694` use the two new fields. Behaviour with the
   defaults is unchanged.
3. **`tests/fakes/process.py`** gains:
   - `ScriptedProcess` (`SpawnedProcessInterface`):
     - it is built from `lines: Sequence[bytes]`, `stderr: bytes = b""`, `exit_code: int = 0`,
       `hang: bool = False` and `pid`;
     - `stdout` and `stderr` are `asyncio.StreamReader`s, fed and closed when spawned;
     - when the spawner passed a file object for `stdout`, it writes the lines there instead;
     - `wait()` returns `exit_code`. With `hang`, it waits until `terminate()` or `kill()`,
       which set `returncode` to `-15` or `-9`;
     - `communicate()` follows the stdlib's shape;
     - `terminated` and `killed` are flags.
   - `ScriptedProcessSpawner` (`ProcessSpawnerInterface`) scripts `ScriptedProcess`es by argv
     prefix, where the longest prefix wins. It records `spawns: list[SpawnRecord]` (`argv`,
     `env`, `cwd`, `start_new_session`). An unscripted argv raises
     `FileNotFoundError(2, "No such file or directory", argv[0])`, as the real spawn does for
     a missing binary.
4. **Switch the test module.** Every patch listed in *Why* becomes injection:
   - `spawner=ScriptedProcessSpawner(...)`;
   - `locator=FakeExecutableLocator(...)`;
   - `runner=ScriptedSyncCommandRunner(...)`;
   - `python_env=OrchestratorPythonEnv(interpreter=FakeInterpreterPrefix(...))`;
   - for "a process that never exits": `ScriptedProcess(hang=True)` with
     `stop_wait_seconds=0.05` and `stop_terminate_seconds=0.05`, in place of patching
     `asyncio.wait_for`.
   `module.asyncio` and `module.shutil` references disappear. Lower the baseline to what
   remains (target: zero).
5. **Split the work into three commits in one lane**, if that helps review: (a) the seam and
   the fields, (b) the fakes and their tests, (c) the test module conversion.

## Where to change
- `src/vibey/infrastructure/interfaces/process_interface.py`, `src/vibey/infrastructure/engines/loop_process_adapter.py`.
- `tests/fakes/process.py`, `tests/fakes/test_fake_process.py` (appended), `tests/fakes/registry.py`,
  `tests/meta/patching_baseline.json`, `tests/infrastructure/engines/test_loop_process_adapter.py`.

## Acceptance criteria
- [ ] `grep -c "monkeypatch.setattr\|patch(" tests/infrastructure/engines/test_loop_process_adapter.py` prints `0`.
- [ ] The number of tests in that module is unchanged.
- [ ] `tests/live/**` (protected, real in-tree binaries through the production spawner) passes unchanged.
- [ ] 100% `infrastructure/` coverage.

## Tests to write first (TDD)
Appended to `tests/fakes/test_fake_process.py`:
- `test_scripted_process_streams_lines_then_exits`
- `test_scripted_process_writes_to_a_file_stdout`
- `test_hanging_process_waits_until_terminated`
- `test_spawner_records_env_cwd_and_session`
- `test_unscripted_argv_is_file_not_found`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure/engines tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The opencodeloop adapter (being retired).
- Loop services (ADR-0044 R22–R26 own their own seams).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-process-executor`, `split-367-2-process-launcher` (it owns `ProcessSpawnerInterface` and the adapter's `spawner`/`resolver` seams; see item 0).
- **Files touched:** see *Where to change*.
- **Shares a file with:** `loop_process_adapter.py` (R20 extracts the run directory, and R25
  and R28 add the loop-service invocation). If they have landed, rebase. The new fields are
  appended after the existing ones.
- **Must keep passing unchanged:** `tests/live/**` and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
