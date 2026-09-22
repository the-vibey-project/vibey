## Title
feat(test-harness): pytest's queue mode puts the run on the harness and prints its answer

## Why
Draft ADR-0045 §10. With `vibey_harness_route = queue`, a plain `uv run pytest …` builds a request
from its own argv and working directory, puts it on the harness, prints the answer and exits with
its code; pytest itself runs nothing in the requester. That is how a storm lane's model, a reviewer,
or `build.verify` in a vibey worktree reaches the queue **without knowing** (8.e, ratified,
`src/vibey_tools/gh/docs/doctrines.md:274-276`: "a storm lane … put[s] [its] run on the queue").

The plugin short-circuits in `pytest_cmdline_main` with `tryfirst=True` (harness-T07), so no
conftest's `pytest_configure` runs in the requester, and nothing is set up for a run answered from
its record. A **broken** harness must neither pass silently nor run unrouted, so any exception is
exit 3 with the bypass named. A **missing prerequisite** (no writable `state_dir`, no command
executable) is amendment A6's announced direct run; lane fakes-harness-degrade adds that check for
this mode, and it lands before harness-T28 makes `queue` the default, so this lane keeps T07's exit-3
rule for everything that raises.

## Required behaviour
In `src/vibey/cli/pytest_route.py` (harness-T07's module; add and replace one branch):
1. **`__init__`** gains the keyword
   `composition_factory: Callable[[Mapping[str, str], pytest.Config], TestHarnessCompositionInterface] | None = None`.
   The default builds `build_test_harness(<load_config_from_path(path)>, environ, config_path=path)`
   when `path = config.rootpath / "vibey.toml"` exists, else `build_test_harness(None, environ)`
   (`vibey.bootstrap.build_test_harness`, harness-T15a; `load_config_from_path`,
   `src/vibey/infrastructure/config_loader.py:83`).
2. **The `QUEUE` branch** of `pytest_cmdline_main` returns `self._queued(config)`, replacing
   T07's `pytest.UsageError`.
3. **`_queued(self, config) -> int`**:
   1. `composition = self._composition_factory(environ, config)`;
   2. `result = asyncio.run(self._request(composition, config))`, which awaits `composition.client()`
      and `client.request(cwd=Path(config.invocation_params.dir), argv=tuple(config.invocation_params.args), gates=(), fresh=environ.get("VIBEY_HARNESS_FRESH") == "1", grant=False, environ=dict(environ))`;
   3. write `TestRunReport().render(result, announcement=composition.announcement)` plus a newline
      to `sys.stdout` (the stream is injected: add a `stdout: TextIO | None = None` keyword beside
      `stderr`), and flush;
   4. return `TestRunReport().exit_code(result)` (`vibey.cli.test_harness`, harness-T15b);
   5. any exception writes `vibey test-harness: <exc>; bypass with VIBEY_HARNESS_ROUTE=off` to
      stderr and returns 3.
4. **The interface** (`src/vibey/cli/interfaces/pytest_route_interface.py`) is unchanged: `_queued` and `_request` are private.

## Where to change
- `src/vibey/cli/pytest_route.py` (with `edit_file`).
- `tests/cli/test_pytest_route.py`: replace T07's `test_queue_is_refused_in_this_build` with
  `test_queue_renders_the_answer_and_returns_its_code` (the only edit to an existing test), and append the rest.

## Acceptance criteria
- [ ] With `InMemoryTestHarnessComposition` (`tests/fakes/harness_composition.py`) injected through `composition_factory`, queue mode renders the answer, returns its code, and nothing runs pytest (the in-test config's `invocation_params.args` reach `ScriptedHarnessClient.requests[0]["argv"]` unchanged).
- [ ] **End to end** (a subprocess, marked `slow`): a scratch git repository at `tmp_path / "repo"` holding `pytest.ini` (`[pytest]\nvibey_harness_route = queue\n`), a `.gitignore` with `__pycache__/`, one passing test, a `vibey.toml` like harness-T15's end-to-end one (with `state_dir = "<tmp_path>/state"`, `root = "<tmp_path>"`, `database_env = ""` and `command = ["<sys.executable>", "-m", "pytest", "-p", "no:cacheprovider"]`), and a `conftest.py` whose `pytest_configure` appends a line to the absolute path `<tmp_path>/configured.txt` (outside the repository, so it never changes the tested tree); everything committed.
  1. `[sys.executable, "-m", "pytest", "-q"]` in the repository (child environment without `VIBEY_HARNESS_RUN`, `VIBEY_HARNESS_ROUTE`, `VIBEY_TEST_DATABASE_URL`): stdout starts `vibey test-harness: backend=local`, contains the child's `1 passed`, and exits 0.
  2. `configured.txt` has **one** line, written by the child: the requester never ran `pytest_configure`, which checks the `tryfirst` short-circuit (ADR-0045 *Verification owed*).
  3. Run again: the first line says `reused`, and `configured.txt` still has one line.
- [ ] The line printed from `pytest_cmdline_main` reaches the subprocess's stdout, which checks that global capture is suspended by then (ADR-0045 *Verification owed*).
- [ ] A composition that raises gives exit 3 and names the bypass.
- [ ] 100% coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
In `tests/cli/test_pytest_route.py`:
- `test_queue_renders_the_answer_and_returns_its_code` (replaces `test_queue_is_refused_in_this_build`)
- `test_queue_honours_fresh_from_the_environment`
- `test_queue_failure_is_exit_3_and_names_the_bypass` (`InMemoryTestHarnessComposition(fail_client=RuntimeError("boom"))`)
- `test_default_composition_factory_reads_the_rootpath_vibey_toml` (a `tmp_path` `vibey.toml` with a `[test_harness]` `state_dir` under `tmp_path`; the factory's composition carries it)
- `test_end_to_end_queue_runs_once_then_reuses` (`@pytest.mark.slow`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py tests/meta tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Switching the root ini to `queue` (harness-T28). The missing-prerequisite degrade for this mode (fakes-harness-degrade).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T07-pytest-lock-route, harness-T15-test-run-cli.
- **Files touched:** `src/vibey/cli/pytest_route.py`, `tests/cli/test_pytest_route.py`.
- **Shares a file with:** `cli/pytest_route.py` (harness-T07 before; fakes-harness-degrade after, which appends `HarnessPrerequisites` and its tests).
- **Must keep passing unchanged:** every other harness-T07 test, the whole root suite (the root ini is still `locked`), and the protected tests.
- **Registry (amendment A4):** nothing new; the composition it takes is registered by harness-T15a.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv` and `delenv` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Never touch the real machine lock: state directories under `tmp_path`; child environments drop `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE`.
  - The `slow` end-to-end test bounds each subprocess with `timeout=60`; every other wait is under 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
