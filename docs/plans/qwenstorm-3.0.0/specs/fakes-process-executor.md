## Title
test(fakes): process execution, executable lookup, the interpreter prefix and the group kill become declared seams with scripted in-memory fakes

## Why
`CommandExecutor` (`src/vibey/infrastructure/interfaces/__init__.py:72-73`) is already the
seam for "run this argv". `fakes-registry` lists it as `PENDING` under this lane. Several
adapters bypass it, and their tests patch the stdlib:
- `container/runtime.py`: `OciContainerExecutor` calls `shutil.which` (`:25`, `:30`) and
  `asyncio.create_subprocess_exec` (`:80`). Its tests set `shutil.which` and
  `asyncio.create_subprocess_exec` (`tests/infrastructure/container/test_runtime.py:97-171`).
- `notify/desktop.py:33` calls `asyncio.create_subprocess_exec`, and
  `tests/infrastructure/notify/test_publishers.py:328` patches it.
- `engines/claudeloop_process.py:34-53`: `AsyncSubprocessExecutor` is covered by patching
  `asyncio.create_subprocess_exec` (`tests/infrastructure/engines/test_claudeloop_process.py:64,293`).
- `git/clean_env.py`: `CleanGitEnvSubprocessExecutor` is covered the same way
  (`tests/infrastructure/git/test_clean_env.py:29`).
- `process/python_env.py:23-33`: `OrchestratorPythonEnv` reads `sys.prefix` and
  `sys.base_prefix`, which the tests overwrite (`test_python_env.py:20-47`,
  `tests/infrastructure/test_gate_runner.py:152-195`).
- `process/reaper.py:83`: `os.killpg` is replaced in `test_reaper.py:126`.
- `postgres.py:93,148` already has a `Which` type and injects it, which is the pattern to copy.
  Its `_run_command` (`:116-130`) is a module function around `subprocess.run`, and
  `tests/infrastructure/test_postgres_local.py:574-592` patches it.

A real subprocess of **this test's own interpreter** (`sys.executable -c ...`) is not an
outside service. The real executors are tested that way, so their coverage needs no patching,
and every consumer is tested against a scripted fake.

## Required behaviour
1. **Seams.** In `src/vibey/infrastructure/interfaces/`:
   - `ExecutableLocator` (`which(name: str) -> str | None`), with the production
     `PATH_LOCATOR: Final` (a class calling `shutil.which`). `postgres.py`'s `Which` alias
     stays as a type alias, and `PATH_LOCATOR.which` satisfies it;
   - `SyncCommandRunner` (`run(argv: tuple[str, ...], *, timeout: float) -> CommandResult`),
     with `SUBPROCESS_RUNNER: Final` wrapping today's `_run_command` logic in a class;
   - `InterpreterPrefix` (`prefix() -> str` and `base_prefix() -> str`), with
     `SYS_PREFIX: Final` reading `sys`;
   - `ProcessGroupKiller` (`killpg(pid: int, sig: int) -> None`), with `OS_KILLPG: Final`.
   Each is added to `DRIVER_SEAMS` in `tests/fakes/registry.py`.
2. **Inject them.**
   - `OciContainerExecutor(*, runtime_binary=None, runner=None, locator: ExecutableLocator = PATH_LOCATOR)`.
     When no `runner` is given, the default becomes a `CommandExecutor`
     (`AsyncSubprocessExecutor`), not a direct `create_subprocess_exec`. Keep the
     `runner` callable signature it already accepts.
   - `DesktopNotifier(..., executor: CommandExecutor = AsyncSubprocessExecutor())`.
   - `OrchestratorPythonEnv(environ=None, *, interpreter: InterpreterPrefix = SYS_PREFIX)`.
   - `ProcessReaper(..., killer: ProcessGroupKiller = OS_KILLPG)`.
   - `PostgresLocalService(..., runner: SyncCommandRunner = SUBPROCESS_RUNNER)`.
   - `SubprocessGateRunner` takes the `OrchestratorPythonEnv` it uses, if it builds one
     itself (`build/gate_runner.py:61-`).
3. **`tests/fakes/process.py`**:
   - `ScriptedCommandExecutor` (`CommandExecutor`) matches `argv` prefixes. The longest
     scripted prefix wins. It gives a `CommandResult`, or raises a scripted exception. An
     unscripted argv returns `CommandResult(127, "", f"{argv[0]}: command not found")`. It
     records `calls`. `az_cli`'s `FakeExecutor` (`tests/infrastructure/azure/test_az_cli.py:84-`)
     becomes this.
   - `ScriptedSyncCommandRunner`, the same for `SyncCommandRunner`, plus
     `timeout_on(prefix)`, which raises `subprocess.TimeoutExpired`.
   - `FakeExecutableLocator(paths: Mapping[str, str])` answers `which`.
   - `FakeInterpreterPrefix(prefix, base_prefix)`.
   - `RecordingProcessGroupKiller(refuse: BaseException | None = None)` records `(pid, sig)`,
     or raises `refuse`, which covers `ProcessLookupError` and `PermissionError`.
4. **Tests of the real executors run real, hermetic processes.** `AsyncSubprocessExecutor`,
   `CleanGitEnvSubprocessExecutor` and `SUBPROCESS_RUNNER` are tested with
   `(sys.executable, "-c", ...)`: exit codes, stdout and stderr decoding, cancellation, and
   (for clean env) that no `GIT_*` variable reaches the child. No stdlib patching is left.
5. **Switch the consumer tests.** Replace every patch listed in *Why* with injection:
   - `test_runtime.py`, `test_publishers.py` (the desktop test), `test_claudeloop_process.py`,
     `test_clean_env.py`;
   - `test_python_env.py`, `test_gate_runner.py`, `test_reaper.py`, `test_postgres_local.py`;
   - `test_az_cli.py`.
   Lower each file's baseline.
   `tests/infrastructure/engines/test_opencodeloop_process.py` is left alone: opencode is
   being retired. Its baseline entry stays, and the commit body says why.

## Where to change
- New `src/vibey/infrastructure/interfaces/process_interface.py`; `src/vibey/infrastructure/interfaces/__init__.py`.
- `src/vibey/infrastructure/container/runtime.py`, `notify/desktop.py`, `process/python_env.py`,
  `process/reaper.py`, `postgres.py`, `build/gate_runner.py` (constructor keywords and defaults).
- New `tests/fakes/process.py`, `tests/fakes/test_fake_process.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json` and the nine test modules in behaviour 5.

## Acceptance criteria
- [ ] `grep -n "monkeypatch.setattr\|patch(" <the nine modules>` prints nothing.
- [ ] `CommandExecutor` is registered, and its `PENDING` line is gone.
- [ ] 100% `infrastructure/` coverage, bandit clean, `lint-imports` clean.

## Tests to write first (TDD)
`tests/fakes/test_fake_process.py`:
- `test_scripted_executor_longest_prefix_wins_and_unknown_is_127`
- `test_scripted_executor_raises_what_it_was_given`
- `test_sync_runner_can_time_out_on_cue`
- `test_locator_prefix_and_killer_fakes`
- `test_real_async_executor_runs_this_interpreter` (`sys.executable -c "import sys; print('o'); print('e', file=sys.stderr); sys.exit(3)"`)
- `test_real_clean_env_executor_strips_git_variables`
- `test_real_sync_runner_times_out` (`sys.executable -c "import time; time.sleep(5)"`, timeout 0.2)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `engines/loop_process_adapter.py`, whose streaming processes are `fakes-process-spawner`'s job.
- `cli/main.py`'s own `subprocess.run` and `shutil.which` (`fakes-cli-composition`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/live/**` (protected; they spawn the in-tree loop
  binaries) and `tests/infrastructure/engines/test_opencodeloop_process.py`.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
