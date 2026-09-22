## Title
feat(cli): vibey test run puts a run on the harness and waits for its answer

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:274-276`): "a commit hook, a
storm lane, a reviewer and the command line all put their run on the queue and wait for its
result". Draft ADR-0045 §10 and §11 give that a command. It prints the answer with a first line
that says what happened (executed, reused, flaky, parked, saturated, still running) and exits with
a code a hook or a model can act on: the recorded pytest code, 1 for a gate failure, 75 for "not
yet", 3 (`EXIT_BLOCKED`, `src/vibey/cli/errors.py:35`) for a park or a dead letter. A reused
answer always says it was reused and when it was recorded (10.f).

This lane adds the command class, the report and the `test` typer group in
`src/vibey/cli/test_harness.py`; harness-T15c registers the group with `vibey`, and harness-T15
adds the supervisor command.

## Required behaviour
Create `src/vibey/cli/test_harness.py`, following `src/vibey/cli/ledger_search.py` (a command
class holds the logic; thin module-level typer functions carry the reason comment at
`src/vibey/cli/ledger_search.py:275-276`):
1. **`TestRunReport`**, stateless:
   - `render(self, result: TestRunResult, *, announcement: str | None, full_log: str | None = None) -> str`,
     the lines in order:
     1. `vibey test-harness: backend=<result.backend> run=<run_id or -> key=<first 12 of key or -> <word>`,
        where `<word>` is `flaky` when `result.flaky`, else `executed`, `reused`, `parked`,
        `saturated` or `still running` for the status;
     2. the announcement, if any;
     3. `full_log` if given, else `result.output_tail` (omitted when empty);
     4. one line per gate: `gate <include> >= <n>%: passed`, or `gate <include> >= <n>%: FAILED (exit <c>)` followed by that gate's output;
     5. `result.detail`, if any;
     6. for `PARKED`, or an outcome whose `is_dead_letter()`:
        `dead-lettered: <outcome> — see "vibey test dead-letters"; requeue with "vibey test requeue <run_id>"`;
     7. for `REUSED`: `(recorded <recorded_at isoformat>; add --fresh to run it again)`.
   - `exit_code(self, result: TestRunResult) -> int`: `SATURATED` and `STILL_RUNNING` → 75;
     `PARKED` or a dead-letter outcome → `EXIT_BLOCKED` (3); `PASSED` → 0; `FAILED` →
     `result.exit_code` when set and non-zero, else 1; `ABANDONED` → 1.
2. **`TestRunCommand(*, composition_factory: Callable[..., TestHarnessCompositionInterface] = build_test_harness, report: TestRunReportInterface | None = None, config_loader: Callable[[Path], VibeyConfig] = load_config_from_path)`**
   (`build_test_harness` from `vibey.bootstrap`, harness-T15a; `load_config_from_path` from
   `vibey.infrastructure.config_loader:83`).
   `run(self, *, args: Sequence[str], gates: Sequence[str], fresh: bool, backend: str | None, wait_seconds: int | None, cwd: Path | None, config: Path | None, full_output: bool, environ: Mapping[str, str]) -> int`:
   1. `env = dict(environ)`; `backend` sets `env["VIBEY_HARNESS_BACKEND"]`; `wait_seconds` sets
      `env["VIBEY_HARNESS_WAIT_SECONDS"] = str(wait_seconds)`; `fresh` is also on when
      `env.get("VIBEY_HARNESS_FRESH") == "1"`.
   2. The config path is `config` when given, else `Path("vibey.toml")` when that file exists,
      else `None`; the config is `config_loader(path)` or `None`. The factory is called as
      `composition_factory(<config>, env, config_path=<path>)`, so the supervisor reads the same file.
   3. `parsed = [CoverageGate.parse(g) for g in gates]`; a `ValueError` echoes its message to
      stderr and returns `EXIT_USAGE` (2, `src/vibey/cli/errors.py:34`).
   4. `result = asyncio.run(self._request(...))`, where `_request` awaits `composition.client()` and
      `client.request(cwd=(cwd or Path.cwd()).resolve(), argv=tuple(args), gates=tuple(parsed), fresh=fresh, grant=False, environ=env)`.
      `TestHarnessNotConfigured` (harness-T05) echoes its message to stderr and returns 2.
   5. Echo `report.render(result, announcement=composition.announcement, full_log=<Path(result.log_path).read_text(errors="replace") when full_output and result.log_path names an existing file, else None>)`
      and return `report.exit_code(result)`.
3. **Typer.** `test_app = typer.Typer(name="test", no_args_is_help=True)` and a command
   `run`, declared with `context_settings={"allow_extra_args": True, "ignore_unknown_options": True}`:
   ```
   vibey test run [--gate INCLUDE=MIN]... [--fresh] [--backend auto|local|rabbitmq]
                  [--wait-seconds N] [--cwd DIR] [--config FILE] [--full-output] -- PYTEST_ARGS...
   ```
   Its module-level function takes `ctx: typer.Context`, finds the command with
   `ctx.find_object(TestRunCommand) or TEST_RUN` (the declared seam: tests pass
   `CliRunner.invoke(test_app, [...], obj=TestRunCommand(...))`), calls
   `run(args=ctx.args, ..., environ=os.environ)`, and raises `typer.Exit(code=...)`.
   `TEST_RUN = TestRunCommand()` is a module-level binding with a reason comment (the typer
   function needs a default command object; it holds no state beyond its collaborators).
4. **Interfaces**, new `src/vibey/cli/interfaces/test_harness_interface.py`:
   `@runtime_checkable` `TestRunReportInterface` (`render`, `exit_code`) and
   `TestRunCommandInterface` (`run`). Do not edit `src/vibey/cli/interfaces/__init__.py`.

## Where to change
- New `src/vibey/cli/test_harness.py` and `src/vibey/cli/interfaces/test_harness_interface.py`.
- New `tests/cli/test_test_harness_cli.py`. Do not register the group in `cli/main.py` here (harness-T15c does).

## Acceptance criteria
- [ ] The report's first line, and the exit code, are right for every status and outcome.
- [ ] `vibey test run` (invoked on `test_app` through `CliRunner` with `obj=TestRunCommand(composition_factory=...)` returning an `InMemoryTestHarnessComposition` from `tests/fakes/harness_composition.py`) passes the arguments after `--` to the client unchanged, renders the scripted answer, and exits with its code.
- [ ] A bad `--gate` exits 2. A composition whose `client()` raises `TestHarnessNotConfigured` exits 2 with its message.
- [ ] 100% coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/cli/test_test_harness_cli.py` (`from vibey.cli import test_harness as th_cli`;
`runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})` as in
`tests/cli/test_ledger_search_cli.py:44`; scripted results through `ScriptedHarnessClient`):
- `test_report_first_line_for_each_status` (parametrized, including `flaky`)
- `test_report_lists_gates_detail_park_and_reuse_lines`
- `test_exit_code_table` (parametrized)
- `test_run_passes_args_after_the_double_dash`
- `test_run_sets_backend_and_wait_in_the_environment`
- `test_bad_gate_exits_2`
- `test_not_configured_exits_2_with_its_message` (`InMemoryTestHarnessComposition(fail_client=TestHarnessNotConfigured("… export VIBEY_HARNESS_BACKEND=local"))`)
- `test_fresh_from_the_environment` (`monkeypatch.setenv("VIBEY_HARNESS_FRESH", "1")`)
- `test_full_output_prints_the_log` (a result whose `log_path` is a file under `tmp_path`)
- `test_config_file_is_loaded_and_passed_on` (a `vibey.toml` under `tmp_path` via `--config`; the factory records its arguments)
- `test_command_and_report_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Registering the group with `vibey` and `python -m vibey` (harness-T15c).
- The supervisor command (harness-T15), `status`/`dead-letters`/`requeue` (harness-T16), `serve` (harness-T25).
- CHANGELOG.md, docs/ (`docs/reference/cli.md` is the docs wave's), ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15a-test-harness-composition.
- **Files touched:** `src/vibey/cli/test_harness.py` (new), `src/vibey/cli/interfaces/test_harness_interface.py` (new), `tests/cli/test_test_harness_cli.py` (new).
- **Shares a file with:** `src/vibey/cli/test_harness.py` (harness-T15, T16, T25 add to it later).
- **Must keep passing unchanged:** `tests/cli/*`, `tests/fakes/*`, and the protected tests.
- **Registry (amendment A4):** nothing new. The commands are not injected anywhere; the composition they take is registered by harness-T15a.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names (`th_cli.TestRunCommand`).
  - Substitute only at a declared seam: `CliRunner.invoke(..., obj=...)` and constructor keywords. Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): the in-memory composition spawns nothing.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
