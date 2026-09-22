## Title
feat(vibey-gh): the merge train, the review commands and promotion record their duration and outcome

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) measures every lane; the merge
train, the review gate and promotion are the delivery lanes vibey-gh runs, and today they record
nothing. Every vibey-gh command is dispatched at one line, `return int(args.func(args))`
(`src/vibey_tools/gh/vibey_gh/cli.py:1882-1883`), after `parse_args` has set `args.cmd`
(`:1247`) and, for `pr-automation`, `args.action` (`:1313`). Timing the measured commands there,
and appending each measurement to the log of lane `gap-measure-gh-1`, measures them all without
touching `merge_train`, `pr_automation`, `local_review` or `promote`. #134's feasibility probes
(`issue-audit/updates/134.md`, `vibey-gh estimate`) are a different thing and are not duplicated:
they predict a job before it runs; this records what each delivery command took once it ran.

Where the log lives is a declared key (12.c, `:455`): `[measure] log` in `.vibey-gh.toml`,
default `.vibey/measurements.jsonl`, overridden by `VIBEY_MEASURE_LOG`.

## Required behaviour
1. `src/vibey_tools/gh/vibey_gh/config.py`: `GhConfig` gains, after `estimate` (`:1511`), with a
   one-line comment "where `vibey-gh` appends its measurements (8.g); repository-relative",
   `measurement_log: str = ".vibey/measurements.jsonl"`; `load_config`'s `GhConfig(...)` call
   (ends `:1958`) passes `measurement_log=str(data.get("measure", {}).get("log",
   ".vibey/measurements.jsonl"))`. `GhConfig.__post_init__` (`config.py:1546`) raises
   `ValueError("measure.log must be a non-empty path")` when it is empty or only whitespace.
2. New `src/vibey_tools/gh/vibey_gh/command_meter.py`:
   - `MEASURED_COMMANDS: Final = frozenset({"merge-train", "local-review", "pr-automation", "promote"})`,
     `MEASURE_LOG_ENV: Final = "VIBEY_MEASURE_LOG"`.
   - `class CommandMeter(CommandMeterInterface)`: `__init__(self, *, path: Path, log:
     MeasurementLogInterface | None = None, now: Callable[[], datetime] | None = None,
     monotonic: Callable[[], float] = time.monotonic, ids: Callable[[], str] | None = None,
     instance: str = "", stderr: TextIO | None = None)`; `None` defaults are `MeasurementLog()`,
     `lambda: datetime.now(UTC)`, `lambda: str(uuid.uuid4())` and `sys.stderr`.
   - `@classmethod for_repository(cls, cfg: GhConfig, environ: Mapping[str, str] = os.environ)
     -> CommandMeter`: `raw = environ.get(MEASURE_LOG_ENV) or cfg.measurement_log`; a relative
     path is joined to `find_root()` (`vibey_gh/config.py:1630`); `instance=platform.node()`.
   - `run(self, command: str, action: str | None, call: Callable[[], int]) -> int`: subject name
     `f"vibey-gh.{command}"`, plus `f".{action}"` when `action` is set. It notes `started = now()`
     and `t0 = monotonic()`, then:
     - `code = call()` → outcome `"ok"` if `code == 0` else `"failed"`, detail `f"exit {code}"`,
       returns `code`;
     - `KeyboardInterrupt` → `"cancelled"`, detail `"interrupted"`, re-raised;
     - `SystemExit as exc` → `"ok"` when `exc.code in (0, None)` else `"failed"`, detail
       `f"exit {exc.code}"`, re-raised;
     - any other `BaseException` → `"failed"`, detail `f"{type(exc).__name__}: {exc}"[:500]`,
       re-raised.
     Each case appends exactly one payload: `{"schema": MEASUREMENT_SCHEMA, "measurement_id":
     ids(), "subject": {"kind": "lane", "name": name}, "instance": instance, "outcome": outcome,
     "started_at": started.isoformat(), "ended_at": now().isoformat(), "readings":
     {"latency_seconds": max(0.0, monotonic() - t0)}, "detail": detail, "causation_id": None}`.
     An `OSError` or `ValueError` from `append` is written as
     `f"vibey-gh: measurement not recorded: {exc}\n"` to `stderr` and never changes the
     command's result — a delivery command does not fail because its log could not be written,
     and the omission is still said aloud (7.c).
3. New `src/vibey_tools/gh/vibey_gh/interfaces/command_meter_interface.py`:
   `CommandMeterInterface` (`run`).
4. `cli.py` `main` (`:1882-1883`) becomes:
   ```python
   args = parser.parse_args(argv)
   if args.cmd in MEASURED_COMMANDS:
       meter = CommandMeter.for_repository(load_config())
       return meter.run(args.cmd, getattr(args, "action", None), lambda: int(args.func(args)))
   return int(args.func(args))
   ```
5. `src/vibey_tools/gh/test/conftest.py`: a second autouse fixture beside
   `_no_ambient_actions_env` (`:43-48`), `_measurements_stay_in_tmp(monkeypatch, tmp_path)`,
   which does `monkeypatch.setenv("VIBEY_MEASURE_LOG", str(tmp_path / "measurements.jsonl"))`,
   so no test ever writes a log into the working tree.

## Where to change
- `vibey_gh/config.py`, `vibey_gh/cli.py` (both `edit_file`), `test/conftest.py`.
- New `vibey_gh/command_meter.py`, `vibey_gh/interfaces/command_meter_interface.py`.
- New `test/test_command_meter.py` (all under `src/vibey_tools/gh/`). Its log is a plain class
  implementing `MeasurementLogInterface` that keeps payloads in a list (or raises on demand).

## Acceptance criteria
- [ ] `run("merge-train", None, lambda: 0)` with `monotonic` stepping 0 → 2.5 appends one payload
      named `vibey-gh.merge-train`, outcome `ok`, `latency_seconds 2.5`, detail `exit 0`.
- [ ] `run("pr-automation", "evaluate", lambda: 1)` is `vibey-gh.pr-automation.evaluate`, `failed`.
- [ ] A raising call is recorded `failed` and re-raised; `KeyboardInterrupt` is `cancelled`.
- [ ] A log that raises `OSError("read-only")` leaves the command's return value unchanged and
      writes `vibey-gh: measurement not recorded: read-only` to the given stderr.
- [ ] `[measure] log = "m.jsonl"` in `.vibey-gh.toml` gives `cfg.measurement_log == "m.jsonl"`;
      `VIBEY_MEASURE_LOG` wins over it; a relative path resolves under the repository root.
- [ ] An AST test finds the `MEASURED_COMMANDS` branch in `cli.main` before the plain dispatch.
- [ ] A payload the meter writes is read back by `MeasurementLog().read` (lane `gap-measure-gh-1`).
- [ ] Every existing vibey-gh test passes; the tenant keeps its 100% floor; `git status` shows no
      `.vibey/measurements.jsonl` after the suite runs.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_command_meter.py`:
- `test_a_successful_command_is_measured_ok`
- `test_a_nonzero_exit_is_measured_failed_with_its_action`
- `test_exceptions_interrupts_and_exits_are_measured_and_reraised` (parametrized)
- `test_a_log_failure_is_reported_and_never_changes_the_result`
- `test_the_log_path_comes_from_config_then_environment`
- `test_main_measures_the_delivery_commands` (the AST check)
- `test_the_meter_writes_what_the_log_reads` (a real `MeasurementLog` on `tmp_path`)
- `test_the_meter_satisfies_its_interface`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git status --porcelain | grep -c "measurements.jsonl" | grep -qx 0

## Out of scope
- Shipping the log from a CI runner to where vibey ingests it (an operator decision: a workflow
  artifact, or a commit to a measurements branch); rendered workflows are not changed here.
- vibey's ingest (`gap-measure-log-ingest`); `vibey-gh estimate` (#134).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(vibey-gh): the merge train, the review commands and promotion record their duration and outcome`. Do not push.

## Lane card
- **Depends on:** `gap-measure-gh-1`.
- **Standing constraints:** as `gap-measure-gh-1` (tenant gates on its floor, black and ruff
  format both, dependency-free, the patching ratchet never raised; `monkeypatch.setenv` only).
- **Must keep passing unchanged:** every vibey-gh test, including `test/test_gh_cli.py`, and the
  managed-automation drift check.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
