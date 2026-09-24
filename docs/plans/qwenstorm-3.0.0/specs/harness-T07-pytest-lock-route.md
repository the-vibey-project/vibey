## Title
feat(test-harness): every root pytest run takes the machine's test lock

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:274-277`): "Nothing starts a
second test run beside a running one", and its measured cause (`:288-292`): a push-hook suite
collided with a storm lane, and two coverage runs in one directory consumed each other's
`.coverage.*` shards (`[tool.coverage.run] parallel = true`, `pyproject.toml:304-307`). The
pre-push stage runs the suite up to three times per push (`.pre-commit-config.yaml:20-23`), and
storm lanes run `uv run pytest` beside the operator's pushes.

Draft ADR-0045 §10 and §15 make a pytest plugin the one route every invocation passes through,
wherever vibey is installed. This lane ships its `locked` mode, which serializes whole runs
before any queue exists, and switches it on for this repository:
- **registration**: a `pytest11` entry point naming a class *instance*, so its hooks are methods (9.b);
- **short-circuit**: `pytest_cmdline_main` with `tryfirst=True` runs before any conftest's
  `pytest_configure`, so nothing is set up yet;
- **mode**: an ini key, overridden by `VIBEY_HARNESS_ROUTE`;
- **re-entrancy**: it marks its own process with `VIBEY_HARNESS_RUN`, so xdist workers and nested runs pass through.

Amendment A6/A7 (`specs/ADR-test-harness-fakes-amendment.md:161-192`): a **missing
prerequisite is not a broken harness**. From this lane on `locked` is the repository default, so
a run whose `state_dir` cannot be written (a sandboxed or read-only home, a container) must
announce it and run directly, not fail before the first test. This lane folds that half of A6
into `locked` mode (A7's first option); lane fakes-harness-degrade later generalizes the check
for `queue` mode and verifies this behaviour is present.

## Required behaviour
Create `src/vibey/cli/pytest_route.py`:
1. **`class PytestHarnessRoute`**:
   - `INI_NAME: ClassVar[str] = "vibey_harness_route"`.
   - `PASS_THROUGH: ClassVar[frozenset[str]]` is exactly `--help`, `-h`, `--version`, `-V`,
     `--fixtures`, `--fixtures-per-test`, `--markers`, `--collect-only` and `--co`.
   - `__init__(self, environ: MutableMapping[str, str] | None = None, *, settings_loader: Callable[[Mapping[str, str]], TestHarnessSettingsInterface] | None = None, lock_factory: Callable[[Path], MachineLockInterface] | None = None, stderr: TextIO | None = None)`.
     Defaults: `os.environ`, `lambda env: TestHarnessSettings.from_sources(None, env)`,
     `MachineLock` (harness-T06) and `sys.stderr`. The environment is read at call time, never cached.
   - `pytest_addoption(self, parser: pytest.Parser) -> None` calls
     `parser.addini(self.INI_NAME, "how pytest runs reach vibey's test harness: off, locked or queue (ADR-0045)", default="off")`.
   - `mode(self, config: pytest.Config) -> TestRouteMode`: `VIBEY_HARNESS_ROUTE` when set and not
     blank, else `config.getini(self.INI_NAME)`, parsed with `TestRouteMode.parse`
     (`vibey.domain.test_harness`). A `ValueError` becomes `pytest.UsageError(str(exc))`.
   - `@pytest.hookimpl(tryfirst=True) def pytest_cmdline_main(self, config: pytest.Config) -> int | None`,
     in order:
     1. `"VIBEY_HARNESS_RUN"` in the environment → `None`;
     2. any item of `config.invocation_params.args` in `PASS_THROUGH` → `None`;
     3. `OFF` → `None`. When the ini value is not `off` and the environment forced `off`, first
        write one line to stderr: `vibey test-harness: routing bypassed by VIBEY_HARNESS_ROUTE=off`;
     4. `LOCKED` → `return self._locked(config)`;
     5. `QUEUE` → raise `pytest.UsageError("vibey_harness_route = queue is not available in this build; use off or locked")`.
   - `_locked(self, config) -> int | None`:
     1. `settings = settings_loader(environ)`; a `ValueError` (a bad `VIBEY_HARNESS_*` value)
        becomes `pytest.UsageError(str(exc))`. Then `lock = lock_factory(settings.lock_path)`.
     2. `hold = asyncio.run(lock.acquire(timeout_seconds=settings.wait_seconds, holder={"mode": "locked", "cwd": str(config.invocation_params.dir), "argv": list(config.invocation_params.args)}))`.
     3. **Missing prerequisite (A6).** An `OSError` from step 2 (the state directory or the lock
        file cannot be created or opened) writes
        `vibey test-harness: no writable state_dir {settings.state_dir} ({exc.strerror or exc}); running directly (not serialised, not recorded)`
        to stderr, sets `environ["VIBEY_HARNESS_RUN"] = f"direct-{os.getpid()}"`, and returns `None`.
     4. `hold is None` → write
        `vibey test-harness: the machine's test lock is held by pid <pid> since <since>; waited <n>s. Run the same command again, or bypass with VIBEY_HARNESS_ROUTE=off.`
        to stderr (from `lock.holder()`; "an unknown process" when that is `None`, and `<n>` is
        `settings.wait_seconds`), and return `75`.
     5. Otherwise keep `self._hold = hold` (never released: the OS releases the lock when this
        pytest process exits), set `environ["VIBEY_HARNESS_RUN"] = f"locked-{os.getpid()}"`, write
        `vibey test-harness: locked (one test run at a time on this machine)` to stderr, and return `None`.
2. **`PLUGIN = PytestHarnessRoute()`**, a module-level binding, with the comment:
   `# Module-level: pytest11 entry points name an object; pluggy registers this instance's methods as hooks (ADR-0045 §10).`
3. **`pyproject.toml`**:
   - immediately after the `[project.scripts]` table (`:69-81`), add
     ```toml
     # The test harness's pytest route (ADR-0045 §10): inert unless an ini or
     # VIBEY_HARNESS_ROUTE switches it on.
     [project.entry-points.pytest11]
     vibey_harness_route = "vibey.cli.pytest_route:PLUGIN"
     ```
   - in `[tool.pytest.ini_options]` (`:259-270`), after `addopts` (`:262`), add
     `vibey_harness_route = "locked"` with the comment
     `# 8.e: one test run at a time on this machine (ADR-0045 §15). VIBEY_HARNESS_ROUTE=off bypasses it.`;
   - then run `uv sync --extra dev` so the editable install registers the entry point. If
     `uv lock --check` fails, run `uv lock` and say so in the commit body.
4. **The interface** `src/vibey/cli/interfaces/pytest_route_interface.py` declares
   `@runtime_checkable` `PytestHarnessRouteInterface` with `mode`, `pytest_addoption` and
   `pytest_cmdline_main`. Do not edit `src/vibey/cli/interfaces/__init__.py`.

## Where to change
- New `src/vibey/cli/pytest_route.py` and `src/vibey/cli/interfaces/pytest_route_interface.py`.
  The `cli/` layer may import `vibey.infrastructure`, as `src/vibey/cli/main.py:58-77` does.
- `pyproject.toml` (the entry-point table and one ini line, with `edit_file`).
- New `tests/cli/test_pytest_route.py`.

## Acceptance criteria
- [ ] `importlib.metadata.entry_points(group="pytest11")` holds `vibey_harness_route = vibey.cli.pytest_route:PLUGIN`.
- [ ] A subprocess pytest in a scratch project with `vibey_harness_route = locked` sees `VIBEY_HARNESS_RUN` starting with `locked-`, and exits 0.
- [ ] While the test holds the same (`tmp_path`) lock, that subprocess, with `VIBEY_HARNESS_WAIT_SECONDS=1`, exits 75 and names the holder's pid.
- [ ] With an unwritable `VIBEY_HARNESS_STATE_DIR`, the subprocess prints the `running directly` line and exits 0.
- [ ] The whole root suite passes with the root ini set to `locked`.
- [ ] 100% coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/cli/test_pytest_route.py` (`from vibey.cli import pytest_route as pr`). Unit tests use a
fake config, `SimpleNamespace(invocation_params=SimpleNamespace(args=(...), dir=tmp_path), getini=lambda name: value)`,
an injected `environ` dict, `stderr=io.StringIO()`, and `settings_loader=lambda env: TestHarnessSettings.from_sources(None, {**env, "VIBEY_HARNESS_STATE_DIR": str(tmp_path / "state"), "HOME": str(tmp_path)})`:
- `test_inside_a_run_passes_through`
- `test_pass_through_flags` (parametrized over `PASS_THROUGH`)
- `test_off_passes_through`
- `test_env_beats_the_ini`
- `test_forced_off_names_the_bypass`
- `test_an_invalid_mode_is_a_usage_error`
- `test_a_bad_harness_variable_is_a_usage_error` (`VIBEY_HARNESS_WAIT_SECONDS=soon`)
- `test_queue_is_refused_in_this_build`
- `test_locked_holds_the_lock_and_marks_the_process` (a real `MachineLock` on `tmp_path`; afterwards a second `acquire(timeout_seconds=0.2)` returns `None`)
- `test_locked_times_out_with_75_and_names_the_holder`
- `test_locked_without_a_writable_state_dir_runs_directly` (a `tmp_path` directory with mode `0o500`; skip when running as root). The name differs from lane fakes-harness-degrade's `test_an_unwritable_state_dir_runs_directly_and_says_so` on purpose, so that lane's append cannot redefine it.
- `test_the_entry_point_is_registered`
- `test_end_to_end_locked_run` (subprocess): a scratch dir with `pytest.ini` (`[pytest]\nvibey_harness_route = locked\n`) and `test_x.py` asserting `os.environ["VIBEY_HARNESS_RUN"].startswith("locked-")`. Run `[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]` in it with `VIBEY_HARNESS_STATE_DIR` under `tmp_path` and `VIBEY_HARNESS_RUN`/`VIBEY_HARNESS_ROUTE` removed from the child environment. Expect exit 0.
- `test_end_to_end_waits_for_a_held_lock` (subprocess): hold the `tmp_path` lock in the test and pass `VIBEY_HARNESS_WAIT_SECONDS=1`. Expect 75 and `held by pid` in stderr.

## Checks the lane must run (all must pass)
    uv lock --check
    uv sync --extra dev
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py tests/meta tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `queue` mode (harness-T17) and its prerequisite checks (fakes-harness-degrade).
- `.pre-commit-config.yaml` (harness-T18): the pre-push `uv run pytest` is serialized by this lane's ini with no hook change.
- Tenant `pyproject.toml` files: their CI rows have no vibey installed, and an unknown ini key would warn there.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T05-test-harness-config, harness-T06-machine-lock.
- **Files touched:** the two new source files, `pyproject.toml`, the new test file (and `uv.lock` only if `uv lock --check` requires it).
- **Shares a file with:** `pyproject.toml` (rmq-r03 before; fakes-ci-no-services and harness-T28 after); `src/vibey/cli/pytest_route.py` (harness-T17 and fakes-harness-degrade after).
- **Must keep passing unchanged:** the whole root suite (the plugin loads in every pytest run in this venv, and from this lane on every root run takes the machine lock), `tests/meta/*` (notably `test_githooks_reach_the_framework.py`), `tests/cli/*`, `uv lock --check`, and the protected tests.
- **Registry (amendment A4):** nothing new. The plugin is not injected anywhere; the lock it uses is already pending under harness-T06.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (the constructor keywords above). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out); children of `sys.executable` are inside.
  - Never touch the real machine lock: every settings object points `VIBEY_HARNESS_STATE_DIR` under `tmp_path`, and every child environment drops `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE`.
  - Hermetic commands only (`sys.executable -m pytest -p no:cacheprovider`); no test waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
