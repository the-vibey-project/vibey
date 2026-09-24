## Title
feat(cli): vibey test-harness execute is the local backend's detached instance

## Why
Draft ADR-0045 §1 and §3: with the `local` backend, the instance for a request is a supervisor the
requester spawns detached, `python -m vibey test-harness execute --request-file PATH [--config FILE]`
(harness-T14's `SupervisorSpawner`, composed by harness-T15a). It takes the request from the
store, runs it through the same `HarnessInstance` (harness-T13) that the `rabbitmq` service
uses, and leaves the answer in the store for the waiting requester. A human who stops an unwanted
run sends the lock holder SIGTERM; the instance kills the run's process group and records it
`abandoned` (ADR-0045 §11).

SIGTERM that arrives while the process is still importing is caught by the latch armed at import
(`src/vibey/cli/main.py:7-9`, `src/vibey/cli/early_signals.py`). As the worker does
(`src/vibey/cli/main.py:1515-1540`), the command installs its handler first, then releases the
latch, then acts at once if the latch fired. `release()` only restores the default disposition
while the latch's own handler is still installed (`early_signals.py:64-86`), so the real handler survives.

This is the last part of the T15 split; with it, `vibey test run` works end to end on the
`local` backend.

## Required behaviour
In `src/vibey/cli/test_harness.py` (harness-T15b's module; add, do not rewrite):
1. **`TestHarnessExecuteCommand(*, composition_factory: Callable[..., TestHarnessCompositionInterface] = build_test_harness, latch: SigtermLatchInterface = SIGTERM_LATCH, config_loader: Callable[[Path], VibeyConfig] = load_config_from_path)`**
   (`SIGTERM_LATCH` from `vibey.cli.early_signals`, its interface from
   `vibey.cli.interfaces.early_signals_interface`).
   `run(self, *, request_file: Path, config: Path | None, environ: Mapping[str, str]) -> int`:
   1. build the composition with `composition_factory(<config_loader(config) or None>, environ, config_path=config)`;
   2. `asyncio.run(self._execute(composition, request_file))`, where `_execute`:
      - takes `instance = composition.instance("local")`;
      - installs `loop.add_signal_handler(signal.SIGTERM, ...)` and the same for `SIGINT`, each
        scheduling `instance.abandon_current()` as a task (kept in a set so it is not collected);
      - calls `self._latch.release()`, and when `self._latch.fired`, schedules the abandon at once;
      - awaits `instance.handle(composition.store().take_request(request_file))`;
   3. returns 0 — the answer is in the store. Any exception is echoed to stderr
      (`vibey test-harness execute: <exc>`) and returns 1.
2. **Typer.** `harness_app = typer.Typer(name="test-harness", no_args_is_help=True)` with a
   **hidden** command `execute --request-file PATH [--config FILE]`, whose module-level function
   finds `ctx.find_object(TestHarnessExecuteCommand) or TEST_HARNESS_EXECUTE`, calls
   `run(..., environ=os.environ)` and raises `typer.Exit(code=...)`. `TEST_HARNESS_EXECUTE` is a
   module-level binding with the same reason comment as `TEST_RUN`.
3. **`src/vibey/cli/main.py`**: import `harness_app` beside `test_app` and add
   `app.add_typer(harness_app, name="test-harness")` after `app.add_typer(test_app, name="test")`
   (harness-T15c). Nothing else.
4. **Interface**: `TestHarnessExecuteCommandInterface` (`run`) in
   `src/vibey/cli/interfaces/test_harness_interface.py`.

## Where to change
- `src/vibey/cli/test_harness.py`, `src/vibey/cli/interfaces/test_harness_interface.py`,
  `src/vibey/cli/main.py` (one import name and one line) — all with `edit_file`.
- `tests/cli/test_test_harness_cli.py` (tests appended; new imports go in its import block).

## Acceptance criteria
- [ ] `execute` handles a request file end to end with a real composition on `tmp_path` whose configured command is `(sys.executable, "-c", "print('ok')")`: the store then holds an `EXECUTED`/`PASSED` answer for that request.
- [ ] A latch that already fired abandons the run at once: the instance's `abandon_current` is called (checked with `ScriptedHarnessInstance` through an `InMemoryTestHarnessComposition`).
- [ ] A failing composition exits 1 and names the error.
- [ ] **End to end** (a subprocess, marked `slow`): a scratch git repository at `tmp_path / "repo"`
  (committed, with a `.gitignore` holding `__pycache__/` so bytecode never changes the tree) with one
  passing test, and **outside it**, so nothing the harness writes changes the tested tree,
  `tmp_path / "vibey.toml"`:
  ```toml
  [project]
  name = "scratch"
  [test_harness]
  state_dir = "<tmp_path>/state"
  root = "<tmp_path>"
  database_env = ""
  command = ["<sys.executable>", "-m", "pytest", "-p", "no:cacheprovider"]
  ```
  in the repository, run `[sys.executable, "-m", "vibey", "test", "run", "--config", <that file>, "--", "-q"]` with
  `VIBEY_HARNESS_RUN`, `VIBEY_HARNESS_ROUTE` and `VIBEY_TEST_DATABASE_URL` removed from its
  environment. It exits 0 and line 1 matches
  `^vibey test-harness: backend=local run=\S+ key=[0-9a-f]{12} executed$`. A second run prints
  `reused`; with `--fresh` it prints `executed` again.
- [ ] 100% coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
Appended to `tests/cli/test_test_harness_cli.py`. A fresh, never-armed `SigtermLatch()`
(`vibey.cli.early_signals`) is the latch in the tests, so no process signal disposition changes;
the "fired" case uses a plain in-test latch class whose `fired` is `True`:
- `test_execute_handles_the_request_file`
- `test_execute_abandons_when_the_latch_already_fired`
- `test_execute_failure_exits_1_and_names_it`
- `test_execute_is_hidden_and_registered` (`CliRunner().invoke(main.app, ["test-harness", "--help"])` exits 0; `execute` is not listed)
- `test_end_to_end_executes_then_reuses` (`@pytest.mark.slow`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap.py tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `status`, `dead-letters`, `requeue` (harness-T16); the plugin's `queue` mode (harness-T17); `serve` and the AMQP backend (harness-T25).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15c-python-m-vibey.
- **Files touched:** `src/vibey/cli/test_harness.py`, `src/vibey/cli/interfaces/test_harness_interface.py`, `src/vibey/cli/main.py`, `tests/cli/test_test_harness_cli.py`.
- **Shares a file with:** `cli/test_harness.py` (harness-T15b before; harness-T16 and T25 after); `cli/main.py` (harness-T15c before).
- **Must keep passing unchanged:** harness-T15b's and T15c's tests, `tests/cli/*`, `tests/test_bootstrap.py`, the image contract "every console script is on PATH" (no console script is added), and the protected tests.
- **Registry (amendment A4):** nothing new.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (`obj=` and constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): the end-to-end test's database probe is off (`database_env = ""`), and its children are `sys.executable`.
  - Never touch the real machine lock: every state directory is under `tmp_path`, and every child environment drops `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE`.
  - No single wait longer than 5 s, except the `slow` end-to-end test's subprocesses (bound them with `timeout=60`).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
