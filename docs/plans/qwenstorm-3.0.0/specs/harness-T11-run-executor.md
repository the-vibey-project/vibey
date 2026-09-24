## Title
feat(test-harness): execute one test run, bounded, logged and killed as a group

## Why
Draft ADR-0045 §4 fixes how a run executes: the configured command plus argv, in `cwd`; in a
session of its own, so the whole group can be killed; all output to one log file; bounded by
`run_bound_seconds`; and in an environment that is **exactly** `base_env` from the instance,
plus the request's pass-through values, plus the run marker, plus a private `COVERAGE_FILE`.
Nothing else is inherited, notably no `GIT_*` (a hook's `GIT_DIR` would re-point git inside the
tests, `.githooks/framework-hook.sh:35-53`).

A private `COVERAGE_FILE` removes the second piece of 8.e's evidence
(`src/vibey_tools/gh/docs/doctrines.md:290-292`): two coverage runs in one directory merged each
other's `.coverage.*` shards (`[tool.coverage.run] parallel = true`, `pyproject.toml:304-307`).
The group kill is the family's `ProcessReaper` (`src/vibey/infrastructure/process/reaper.py:45-100`,
interface `src/vibey/infrastructure/process/interfaces/reaper_interface.py:13-26`), not a new one
(10.e). The machine lock's descriptor is passed to the child (`pass_fds`), so the lock outlives a
dead instance (harness-T06). Every run records its machine load at start and end (ADR-0045 §9;
sub-doctrine 8.g, always measured).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/executor.py`:
1. **`MachineLoadReader(*, loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg, cpu_count: Callable[[], int | None] = os.cpu_count)`**:
   `read(self) -> MachineLoad | None` returns `MachineLoad(*loadavg(), cpu_count=cpu_count())`;
   an `OSError` from `loadavg` gives `None` (`MachineLoad` from `vibey.domain.test_harness`).
2. **`ExecutionOutcome`**, `@dataclass(frozen=True, slots=True)`: `exit_code: int | None`,
   `timed_out: bool`, `unexecutable: bool`, `detail: str`, `duration_seconds: float`,
   `output_tail: str`, `load_before: MachineLoad | None`, `load_after: MachineLoad | None`.
3. **`ChildEnvironment(base_env: EnvNamePatternsInterface)`**:
   `build(self, *, instance_environ: Mapping[str, str], request_env: Sequence[tuple[str, str]], run_id: UUID, coverage_file: Path) -> dict[str, str]`
   returns `dict(base_env.select(instance_environ))`, updated with `request_env`, then with every
   name starting `GIT_` removed, then with `VIBEY_HARNESS_RUN = str(run_id)` and
   `COVERAGE_FILE = str(coverage_file)` set.
4. **`TestRunExecutor(*, reaper: ProcessReaperInterface, load: MachineLoadReaderInterface | None = None, tail_bytes: int = 65536)`**
   (`load` defaults to `MachineLoadReader()`):
   - `async def run(self, *, argv: tuple[str, ...], cwd: Path, env: Mapping[str, str], bound_seconds: float, log_path: Path, pass_fds: tuple[int, ...] = ()) -> ExecutionOutcome`:
     1. read `load_before`; `start = time.monotonic()`;
     2. open `log_path` for binary writing, created with mode `0o600` (`os.open(..., os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)`);
     3. `process = await asyncio.create_subprocess_exec(*argv, cwd=str(cwd), env=dict(env), stdin=asyncio.subprocess.DEVNULL, stdout=<log fd>, stderr=asyncio.subprocess.STDOUT, start_new_session=True, pass_fds=pass_fds)`.
        An `OSError` (a missing binary, a missing `cwd`, a permission error) returns
        `unexecutable=True`, `exit_code=None`, `detail=f"cannot execute {argv[0]}: {exc}"`;
     4. keep `process` as the run in flight; `await asyncio.wait_for(process.wait(), bound_seconds)`.
        On `TimeoutError`: `await reaper.kill_and_reap(process)`, `timed_out=True`,
        `detail=f"exceeded the run bound of {bound_seconds:g}s"`;
     5. `exit_code = process.returncode` (negative for a signal);
     6. close the log, clear the in-flight process, read `load_after`, and set
        `output_tail = self.tail(log_path)` and `duration_seconds = time.monotonic() - start`.
   - `tail(self, log_path: Path) -> str`: the last `tail_bytes` bytes of the file, decoded as
     UTF-8 with `errors="replace"`, or `""` when the file is missing.
   - `async def stop(self) -> bool`: kills the process group of the run in flight through the
     reaper and returns `True`; returns `False` when nothing is running.
5. **Interfaces**, `src/vibey/infrastructure/test_harness/interfaces/executor_interface.py`:
   `@runtime_checkable` `TestRunExecutorInterface` (`run`, `tail`, `stop`),
   `ChildEnvironmentInterface` (`build`) and `MachineLoadReaderInterface` (`read`).
6. **The fake**, new `tests/fakes/harness_executor.py`:
   `FixedMachineLoadReader(load: MachineLoad | None = MachineLoad(0.5, 0.4, 0.3, 8))` implements
   `MachineLoadReaderInterface`: `read()` increments `self.reads` and returns the configured load.
7. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
   interface module and the fake module, then:
   - append `FakeRegistration(port=executor_interface.MachineLoadReaderInterface, build=harness_executor.FixedMachineLoadReader, note="a fixed machine load, counted")` to `REGISTRY`;
   - append `TestRunExecutorInterface` and `MachineLoadReaderInterface` to `DRIVER_SEAMS`;
   - add `"TestRunExecutorInterface": "fakes-test-harness"` to `PENDING` (fakes-test-harness
     registers `ScriptedTestRunExecutor`). `ChildEnvironment` is a pure policy, not a seam.

## Where to change
- New `src/vibey/infrastructure/test_harness/executor.py` and its interface module.
- New `tests/fakes/harness_executor.py`; `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_executor.py`.

## Acceptance criteria
- [ ] A command `(sys.executable, "-c", ...)` returns its exit code, and its output lands in the log.
- [ ] `output_tail` is capped at `tail_bytes`.
- [ ] A command that sleeps past the bound is killed with its whole group (a child that spawns a grandchild sleeper; both are gone afterwards), and returns `timed_out`.
- [ ] A missing binary returns `unexecutable`.
- [ ] A descriptor in `pass_fds` is valid in the child.
- [ ] The child's environment is exactly the built one: no `GIT_*`, no name outside `base_env` or the request.
- [ ] pytest-cov honours `COVERAGE_FILE` under xdist with `parallel = true` (ADR-0045 *Verification owed*): in a scratch project with `[tool.coverage.run] parallel = true`, run `(sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-n", "2", "--cov=pkg")` with the built environment; the combined data file exists at `COVERAGE_FILE`, and the scratch directory holds no `.coverage*` file.
- [ ] `uv run --no-sync python -c "import sys; print(sys.prefix)"`, run in `src/vibey_runners/qwen`, prints the repository's `.venv` (ADR-0045 *Verification owed*). This test skips when `shutil.which("uv")` is `None` or `<repo>/.venv` is absent.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_executor.py` (`from vibey.infrastructure.test_harness import executor as ex`;
the real `ProcessReaper(grace_seconds=2.0)`; `FixedMachineLoadReader` where the load does not matter):
- `test_exit_code_and_log`
- `test_signal_exit_is_negative`
- `test_output_tail_is_capped`
- `test_bound_kills_the_group`
- `test_missing_binary_is_unexecutable`
- `test_pass_fds_reach_the_child`
- `test_stop_kills_the_run_in_flight` and `test_stop_with_nothing_running_is_false`
- `test_child_environment_is_exact`
- `test_coverage_file_is_private_under_xdist`
- `test_uv_run_no_sync_uses_the_workspace_venv` (skip-if)
- `test_load_reader_reads_and_handles_oserror` (the default reader returns a `MachineLoad`; `MachineLoadReader(loadavg=<a callable raising OSError>)` returns `None`)
- `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/infrastructure/process tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Coverage gates (harness-T12). Deciding whether to run (harness-T13). The scripted executor fake (fakes-test-harness).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T01-test-run-key, harness-T05-test-harness-config, fakes-registry.
- **Files touched:** the two new source files, `tests/fakes/harness_executor.py` (new), `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** `tests/infrastructure/process/*` (`test_reaper.py` in particular), `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): children of `sys.executable` are inside; `uv` is used by exactly one test, which skips without it.
  - Every child environment a test builds drops `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE` before the executor sets its own marker.
  - No test waits longer than 5 s. POSIX only.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
