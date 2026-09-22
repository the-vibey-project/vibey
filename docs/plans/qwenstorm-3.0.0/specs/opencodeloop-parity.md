# opencodeloop parity: bounded runs, marker-derived completion, exit 75, cost metering

This issue is split into two ordered parts. **Part 1 must be merged before Part 2 starts.**
Each part is a separate lane with its own commit. Each part restates what it needs, so a
lane given only one part has enough to implement it.

Evidence cutoff: `develop` at `d47c196d` (checkout `/private/tmp/claude-501/storm/changelog-2.1.0`),
read on 2026-09-22. The OpenCode event and config shapes were read from `sst/opencode`
branch `dev` on the same date (files named in Part 2).

Paths starting `src/vibey_runners/opencode/` belong to the **tenant**. The tenant layout is
`src/vibey_runners/opencode/src/opencodeloop/{domain,application,infrastructure,cli}` and
`src/vibey_runners/opencode/tests/`. Below, `T/` means `src/vibey_runners/opencode/src/opencodeloop/`
and `TT/` means `src/vibey_runners/opencode/tests/`.

---

# Part 1

## Title
feat(opencodeloop): bound every run, derive completion from the model, and wind down with exit 75

## Why
opencodeloop is the only runner in the family without the shared runner core:
- **Completion is the process exit, not the model.** `T/infrastructure/opencode_process.py:156-164`
  emits `finished` with `success: True` whenever OpenCode exits 0, and `T/infrastructure/run_store.py:45`
  writes `done_marker` whenever `RunResult.succeeded` (`T/domain/model.py:53-56`: FINISHED and exit 0).
  vibey then adds the done marker and `complete: True` to that event (`src/vibey/infrastructure/engines/loop_process_adapter.py:506-524`),
  and `src/vibey/application/build_engine_run.py:114` counts the run as complete. The rest of the family requires
  the model to claim completion: codexloop wants the marker on a line of its own (`src/vibey_runners/codex/src/codexloop/domain/completion.py:128-131`),
  and qwenloop wants the marker plus a verdict (`src/vibey_runners/qwen/src/qwenloop/application/runner.py:273-284`).
  Sub-doctrine 10.f (`src/vibey_tools/gh/docs/doctrines.md:248`): "a verdict is not completion". Here even a
  verdict is missing.
- **No bounds.** The tenant's CLI has no turn, time or stall bound (`T/cli/app.py:52-91`). vibey's DESIGN
  path checks its caps (`src/vibey/infrastructure/engines/opencodeloop_process.py:72-73`) but never sends them
  (`:84` builds argv without them). Compare `claudeloop_process.py:93-103`, which does send them.
- **No exit 75.** The CLI only exits 0, 1 or 2 (`T/cli/app.py:49,65,68,88,91`). vibey starts its no-loss
  handoff only on `EXIT_CODE_WIND_DOWN = 75` (`src/vibey/domain/engine.py:16`, `src/vibey/application/build_implement_handler.py:249-259`, ADR-0004).
- **Real OpenCode text is dropped.** OpenCode writes `{"type":"text",...,"part":{"type":"text","text":"..."}}`.
  `_normalize` (`T/infrastructure/opencode_process.py:194`) turns it into a `text_delta` with no `text` key,
  so vibey's `_last_response` (`src/vibey/infrastructure/engines/opencodeloop_process.py:161-174`) reads nothing
  from a real run.

What "wind-down" means in the family (verified): exit 75 means "I stopped on purpose, hand my work over".
An operator `wind_down` control command triggers it in claudeloop (`claudeloop/application/runner.py:907-912`)
and in qwenloop, where `stop` and `wind_down` both do (`qwenloop/application/runner.py:185-190`, `qwenloop/cli/app.py:245-246`).
claudeloop has two more triggers, a `--wind-down-at` deadline and a headroom policy that is off by default.
A run that runs out of budget, turns or time exits **1**, not 75 (`claudeloop/cli/outcome.py:9-14`).
Capacity or credit exhaustion is not exit 75 either. It is reported as a `capacity.rejected` event, and
vibey checks that before it looks at any exit code (`build_implement_handler.py:241-248`).
This part follows that meaning exactly.

## Required behaviour
1. **The done-marker instruction.** Before `OpencodeRunner.run` sends a prompt (new run or resume), it wraps
   the prompt with the family's shared helper:
   `vibey_runners.common.application.usecases.with_done_marker_instruction(prompt, DONE_MARKER)`, where
   `DONE_MARKER = "OPENCODELOOP_TASK_FULLY_COMPLETE"`. Sub-doctrine 10.e says to use the family's copy,
   so do not write a new one.
2. **Text lifting.** `_normalize` turns an OpenCode line with `type == "text"` whose `part.text` is a str into
   `{"event_type": "text_delta", "text": <part.text>, "raw": <raw>}`. Keep every other mapping as it is.
   `reasoning` events still fall through to a `text_delta` **without** a `text` key.
3. **The completion claim.** The claim is read only from the **last** OpenCode `text` part of the run, that is,
   the last event whose `raw` is a dict with `type == "text"`. It holds when some line of that text, after
   `.strip()`, equals `DONE_MARKER`. A non-JSON stdout line never counts, even if it has `text`.
4. **Terminal status** is decided by one pure rule. Check the conditions in this order:
   - a `capacity.rejected` event was seen → `FAILED` (a capacity rejection always outranks a completion claim);
   - an operator wind-down stopped the run → `STOPPED`;
   - any bound stopped the run → `FAILED`;
   - OpenCode exited non-zero → `FAILED`;
   - there is no completion claim → `FAILED`, with detail `OpenCode exited 0 without the completion marker`;
   - otherwise → `FINISHED`.
5. **Bounds.** `RunBounds(max_turns=40, max_seconds=3600.0, stall_timeout_seconds=900.0)`. Each value is set
   by a CLI flag first, then an environment variable, then this default:
   | flag | env var | meaning |
   |---|---|---|
   | `--max-turns` | `OPENCODELOOP_MAX_TURNS` | most OpenCode steps (model calls) in one invocation; int ≥ 1 |
   | `--max-seconds` | `OPENCODELOOP_MAX_SECONDS` | wall-clock seconds for one invocation; > 0 |
   | `--stall-timeout` | `OPENCODELOOP_STALL_TIMEOUT_SECONDS` | seconds with no stdout line from OpenCode; > 0 |
   An invalid value exits 2 and prints the error to stderr.
   Where the defaults come from: 40 turns is qwenloop's default (`qwenloop/domain/config.py:26`). 900 s is more
   than OpenCode's own longest single shell command, 10 minutes (`sst/opencode packages/core/src/tool/bash.ts:19-20`).
   OpenCode writes a `tool_use` event only when a tool call finishes, so a shorter stall bound would kill a
   legitimate long command.
6. **Turn cap.** Count `turn.completed` events. When a `turn.starting` event arrives and the count is already
   at least `max_turns`, trip `MAX_TURNS` and terminate OpenCode. So a run that finishes in exactly
   `max_turns` steps still succeeds.
7. **Watchdog.** A daemon thread checks the run every `poll_seconds`, which defaults to 1.0 and is a constructor
   argument. It trips, in this order: `WIND_DOWN` if the inbox holds a wind-down request; `MAX_SECONDS` if the
   time since spawn is at least `max_seconds`; `STALL_TIMEOUT` if the time since the last stdout line is at
   least `stall_timeout_seconds`. The first trip wins, and later trips are ignored.
8. **Termination.** Start OpenCode with `start_new_session=True`. To stop it, send `os.killpg(pid, SIGTERM)`,
   then wait `kill_grace_seconds` (constructor argument, default 5.0), then send `os.killpg(pid, SIGKILL)`.
   Ignore `ProcessLookupError` at each step.
9. **Exit codes** come from `RunResult.exit_code`:
   - `FINISHED` → 0
   - `STOPPED` (operator wind-down) → **75**
   - any other status → 1
   - an invalid run id or invalid bounds → 2 (this is how it already works)
10. **Terminal event.**
    - On `FINISHED`, emit `{"event_type":"finished","success":True,"session_id":...}` (as today).
    - Otherwise, emit `{"event_type":"failed","success":False,"detail":...,"stop_reason":<value or None>,"session_id":...}`.
11. **Run files.** `finish()` writes these into `meta.json` and `snapshots/latest.json`:
    - `stop_reason` (a string or null);
    - `exit_code`;
    - `done_marker`, set only when the run is FINISHED (this line already exists, and now it means something).

    The status values are `finished`, `failed` and `stopped`. These are the values that end vibey's tail
    loop (`loop_process_adapter.py:553`).

    `finish()` also writes `stop-summary.md` for **every** terminal state. It holds the status, the stop reason
    and the detail, plus one line with just `DONE_MARKER`, but that line only when the run finished. vibey
    calls `stop()` right after an exit 75 (`build_implement_handler.py:255`), and `stop()` waits up to 30 s
    for this file (`loop_process_adapter.py:659-673`).
12. **Inbox.** `wind_down_requested(run_dir)` returns True when some `run_dir/inbox/*.json` file meets both
    conditions:
    - it was **not already there when `begin()` ran** (keep the names found at `begin()`, so a stale
      `stop.json` from an earlier run with the same run id is ignored when the job is replayed);
    - its JSON object has a `type` or `command` of `stop`, `wind_down` or `wind-down`.

    Skip bad JSON. Never delete these files. vibey already writes `{"command":"stop"}` there
    (`loop_process_adapter.py:653-657`).
13. **CLI `wind-down RUN_ID [--cwd DIR]`** writes `inbox/<time.time_ns()>-wind_down.cmd.json`, which contains
    `{"type":"wind_down","reason":"operator"}`, then prints the file's path and exits 0. An invalid run id exits 2.
    qwenloop has the same command (`qwenloop/cli/app.py:554-556`).
14. **vibey DESIGN path.**
    - `OpenCodeLoopProcess.run` adds `"--max-turns", str(self._max_turns)` after `build_argv(...)`.
    - `_last_response` removes every line whose `.strip()` equals `OPENCODE.done_marker`. The marker is
      protocol, not content, and without this an unfenced JSON answer followed by the marker would fail
      `_looks_structured` and the `_object` parse in `opencodeloop_design.py:160-174`.
15. **CI.** The three `opencodeloop` rows install the shared package first:
    `pip install -e ../common && pip install -e ".[dev]"`, which is the same as the codexloop rows.
    Do **not** add `vibey-runners-common` to the tenant's `dependencies`: it is not on any package index
    (ADR-0037; see the comment at `src/vibey_runners/claude/pyproject.toml:53-56`).

## Where to change
Tenant, domain: `T/domain/model.py` (keep `DONE_MARKER` at `:8`; extend `RunStatus` at `:35-41` and `RunResult` at `:44-56`)
```python
EXIT_CODE_WIND_DOWN = 75  # EX_TEMPFAIL: claudeloop/domain/handoff_marker.py:29, qwenloop/domain/model.py:8
EXIT_CODE_FAILED = 1

class StopReason(StrEnum):
    WIND_DOWN = "wind_down"; MAX_TURNS = "max_turns"; MAX_SECONDS = "max_seconds"; STALL_TIMEOUT = "stall_timeout"

@dataclass(frozen=True, slots=True)
class RunBounds:
    max_turns: int = 40
    max_seconds: float = 3600.0
    stall_timeout_seconds: float = 900.0
    # __post_init__: raise ValueError naming the field when max_turns < 1 or either float is <= 0

class CompletionMarker:          # own-line rule, copied from codexloop/domain/completion.py:128-131
    def __init__(self, marker: str = DONE_MARKER) -> None: ...
    def claimed_by(self, text: str) -> bool: ...   # any(line.strip() == marker for line in text.splitlines())

class TerminalRule:              # capacity-outranks rule, like qwenloop/domain/model.py:111-115
    def decide(self, *, returncode: int, completion_claimed: bool,
               capacity_rejected: bool, stop_reason: StopReason | None) -> RunStatus: ...
```
- `RunResult` gets a new last field, `stop_reason: StopReason | None = None`, so existing positional calls
  still work.
- `RunResult` gets a property `exit_code`: 0 if `succeeded`, `EXIT_CODE_WIND_DOWN` if the status is
  `STOPPED`, otherwise `EXIT_CODE_FAILED`.
- `T/domain/interfaces/model_interface.py` (`:23-40`): add `StopReasonInterface`, `RunBoundsInterface`,
  `CompletionMarkerInterface` and `TerminalRuleInterface`. Add `stop_reason` and `exit_code` to
  `RunResultInterface`. Export all of them from `T/domain/interfaces/__init__.py`.

Tenant, infrastructure: **new** `T/infrastructure/watchdog.py`, class `RunWatchdog`. It follows
`src/vibey_runners/cursor/src/cursorloop/infrastructure/agent/watchdog.py:19-60`.
- `__init__(bounds, *, clock: Callable[[], float], wind_down_requested: Callable[[], bool])` records `started`
  and `last_activity`, both set to `clock()`.
- `reason` is a property.
- `touch()` sets `last_activity`.
- `trip(reason) -> bool` takes a `threading.Lock`. The first reason wins, and the call returns True only
  when it set the reason.
- `check() -> StopReason | None` returns the reason only when **this call** tripped it. It checks, in order:
  wind-down, then `MAX_SECONDS`, then `STALL_TIMEOUT`.

Put its interface in **new** `T/infrastructure/interfaces/watchdog_interface.py`
(`RunWatchdogInterface(Protocol)`) and export it from `T/infrastructure/interfaces/__init__.py`.

Tenant, `T/infrastructure/opencode_process.py`:
- `__init__` (`:39-40`) → `__init__(self, binary="opencode", *, clock=time.monotonic, poll_seconds=1.0, kill_grace_seconds=5.0)`.
- The `execute` signature (`:97-104`) gains `bounds: RunBounds` and `wind_down_requested: Callable[[], bool]`.
- The Popen call (`:124-131`) adds `start_new_session=True`.
- After the stderr reader starts (`:142-143`), create a `RunWatchdog` and start a daemon thread on
  `self._supervise(process, watchdog)`:
  `while process.poll() is None: if watchdog.check() is not None: self._terminate(process); return; time.sleep(self._poll_seconds)`.
- In the stdout loop (`:147-152`), after the blank-line skip:
  - call `watchdog.touch()`;
  - emit the event;
  - a `capacity.rejected` event sets `capacity_rejected`;
  - a `turn.completed` event does `turns += 1`;
  - a `turn.starting` event with `turns >= bounds.max_turns`, where `watchdog.trip(StopReason.MAX_TURNS)` returns True, calls `self._terminate(process)`;
  - if `self._assistant_text(event)` is not None, store it as `final_text`.
- Replace `:153-167`:
  - `returncode = process.wait()`, then join the supervisor thread and the reader thread;
  - `claimed = CompletionMarker().claimed_by(final_text)`;
  - `status = TerminalRule().decide(...)`;
  - emit the terminal event (item 10);
  - return `RunResult(status, returncode, session, detail, watchdog.reason)`. Keep the **raw** returncode.
  Choose `detail` in this order:
  - capacity: `OpenCode reported a capacity rejection`;
  - wind-down: `wound down on request`;
  - a bound: `stopped at bound: <reason.value>`;
  - non-zero exit: the stderr tail, or `OpenCode exited with N` (the existing `:165` logic);
  - no claim: `OpenCode exited 0 without the completion marker`.
- New helper `_terminate(process)` (item 8).
- New static helper `_assistant_text(event) -> str | None`. It returns the event's `text` only when
  `event["raw"]` is a dict with `type == "text"`.
- In `_normalize` (`:183-194`), add the `text` branch (item 2) before the fallthrough.
- Update `T/application/interfaces/process_interface.py:17-25` to the new `execute` signature.

Tenant, `T/infrastructure/run_store.py`:
- Add `__init__`, which sets `self._stale: dict[Path, frozenset[str]] = {}`.
- At the end of `begin()` (`:16-30`), record `self._stale[run_dir]` as the names of the files `inbox/*.json`
  matches.
- Add `wind_down_requested(run_dir) -> bool` (item 12).
- Add `request_wind_down(run_dir) -> Path` (item 13). Create `inbox` with `mkdir(parents=True, exist_ok=True)`.
- In `finish()` (`:37-49`), add `stop_reason` and `exit_code` to `metadata`, then write `run_dir / "stop-summary.md"`.

Also add the two new methods to `T/application/interfaces/store_interface.py:10-20`.
`FileRunStoreInterface` already extends that port, so it needs no change.

Tenant, application, `T/application/runner.py:21-55`:
- `run(*, prompt, run_id, cwd, bounds: RunBounds, session_id=None)` sends
  `with_done_marker_instruction(prompt, DONE_MARKER)`, `bounds=bounds` and
  `wind_down_requested=lambda: self._store.wind_down_requested(run_dir)` to `execute`.
- Add `request_wind_down(*, run_id: str, cwd: Path) -> Path`. It calls
  `self._store.request_wind_down(cwd / ".opencodeloop" / "runs" / RunId.parse(run_id).value)`.
- Mirror both changes in `T/application/interfaces/runner_interface.py:16-24`.

Tenant, CLI, `T/cli/app.py`:
- Add the three options (item 5) to both `run` (`:52-68`) and `resume` (`:71-91`), using `typer.Option(..., envvar="OPENCODELOOP_...")`.
  Take the defaults from `_DEFAULTS = RunBounds()`.
- Build `RunBounds(...)` **inside** the existing `try` blocks, so its `ValueError` exits 2.
- Replace `raise typer.Exit(code=0 if result.succeeded else 1)` with `raise typer.Exit(code=result.exit_code)`.
- Add the `@app.command("wind-down")` command (item 13).

vibey:
- `src/vibey/infrastructure/engines/opencodeloop_process.py:84`: change it to
  `argv = (*build_argv(OPENCODE, spec), "--max-turns", str(self._max_turns))`.
  This follows `claudeloop_process.py:93-103`.
- In the same file, `_last_response` (`:161-174`): join the texts, then drop the marker lines (item 14).

CI: `.github/workflows/ci.yml`, lines **550, 556 and 561**. Change the `install:` value to
`'pip install -e ../common && pip install -e ".[dev]"'`.

## Acceptance criteria
- [ ] `cd src/vibey_runners/opencode && python -m pytest -q` passes. Its `addopts` already enforces 100% branch coverage.
- [ ] `mypy --strict src/opencodeloop`, `lint-imports` and `bandit -q -r src/opencodeloop` pass in the tenant.
- [ ] An OpenCode exit 0 without the marker leaves `meta.json` `status == "failed"`, `done_marker is None` and `exit_code == 1`
      (`test_execute_exit_zero_without_marker_fails`, `test_finish_records_stop_reason_and_exit_code`).
- [ ] An operator wind-down makes the CLI exit 75 (`test_cli_exit_codes_follow_the_family`).
- [ ] A capacity rejection with a marker is still `failed` (`test_execute_capacity_rejection_outranks_a_marker`).
- [ ] `grep -n "start_new_session=True" T/infrastructure/opencode_process.py` finds a match.
- [ ] vibey: `uv run pytest -q -p no:cacheprovider tests/infrastructure/engines/test_opencodeloop_process.py` passes.
- [ ] `grep -c 'pip install -e ../common && pip install -e ".\[dev\]"' .github/workflows/ci.yml` goes up by 3.

## Tests to write first (TDD)
`TT/test_model.py`
- `test_run_bounds_defaults`: checks 40 / 3600.0 / 900.0.
- `test_run_bounds_rejects_invalid_values`: parametrized with `max_turns=0`, `max_seconds=0`, `stall_timeout_seconds=-1`. Each raises `ValueError`.
- `test_completion_marker_requires_its_own_line`: `"done\nOPENCODELOOP_TASK_FULLY_COMPLETE\n"` → True;
  `"  OPENCODELOOP_TASK_FULLY_COMPLETE  "` → True; `"not OPENCODELOOP_TASK_FULLY_COMPLETE yet"` → False; `""` → False.
- `test_terminal_rule_capacity_outranks_a_completion_claim`: `returncode=0, completion_claimed=True, capacity_rejected=True` → FAILED.
- `test_terminal_rule_wind_down_is_stopped`: → STOPPED.
- `test_terminal_rule_fails_on_bound_nonzero_exit_or_missing_marker`: parametrized.
- `test_terminal_rule_finishes_only_on_clean_exit_with_claim`: → FINISHED.
- `test_exit_code_property`: FINISHED/0 → 0; STOPPED → 75; FAILED → 1; FINISHED with returncode 3 → 1.

`TT/test_watchdog.py` (new). Use a `_Clock` object with a settable `now` attribute, passed as `clock=lambda: c.now`.
- `test_check_is_none_within_bounds`.
- `test_check_trips_max_seconds_once`: the second `check()` returns None, and `reason` stays `MAX_SECONDS`.
- `test_touch_resets_the_stall_clock`, then `test_check_trips_stall_timeout`.
- `test_wind_down_outranks_timeouts`.
- `test_first_trip_wins`: `trip(MAX_TURNS)` is True, a second `trip` is False, and `check()` is None.

`TT/test_process.py`
- Extend `_FakeProcess` so that:
  - `pid = 4242`;
  - `wait(timeout=None)` sets `_waited` and returns `returncode`;
  - `poll()` returns `returncode` once `_waited` is set, and None before that.
- Update the existing `execute` tests to pass `bounds=RunBounds()` and `wind_down_requested=lambda: False`.
- Update `test_execute_streams_normalized_events_before_exit` and `test_execute_survives_missing_streams`. With
  no marker, both must now return FAILED and end with a `failed` event carrying detail
  `OpenCode exited 0 without the completion marker`.
- Assert that Popen received `start_new_session=True`.
- `test_execute_finishes_when_the_last_text_part_claims_completion`: the stdout is a `step_start`, a `step_finish`, then
  `{"type":"text","part":{"type":"text","text":"ok\nOPENCODELOOP_TASK_FULLY_COMPLETE"}}` → FINISHED, and the last event is `finished`.
- `test_execute_ignores_a_marker_that_is_not_in_the_last_text_part`, and the same for non-JSON output.
- `test_execute_capacity_rejection_outranks_a_marker`.
- `test_execute_stops_at_the_turn_cap`: `max_turns=2`, with a third `step_start` in the stream. Monkeypatch
  `opencodeloop.infrastructure.opencode_process.os.killpg` to record its calls → it gets `(4242, SIGTERM)`,
  `stop_reason is MAX_TURNS`, and `exit_code == 1`.
- `test_execute_that_finishes_exactly_at_the_cap_succeeds`: `max_turns=1`, one step, then the marker text.
- `test_supervisor_stops_on_max_seconds`. Pass `poll_seconds=0.001`. Use a blocking stdout fake that yields one
  line, sets `clock.now = 10_000`, then waits on a `threading.Event`. The fake `killpg` sets that event. Expect
  `stop_reason is MAX_SECONDS`.
- `test_execute_wind_down_request_stops_with_exit_75`: `wind_down_requested=lambda: True` → STOPPED, exit 75,
  and the last event has `stop_reason == "wind_down"`.
- `test_terminate_escalates_to_sigkill_and_ignores_missing_groups`. The fake's first `wait(timeout=...)` raises
  `subprocess.TimeoutExpired`. Expect SIGTERM and then SIGKILL. A `killpg` that raises `ProcessLookupError` must not crash.
- `test_normalize_lifts_text_from_a_text_part`: `text` → `"text": "hi"`; `reasoning` has no `"text"` key.

`TT/test_store.py`
- `test_finish_writes_stop_summary_with_marker_only_on_success`.
- `test_finish_records_stop_reason_and_exit_code`: STOPPED → `stop_reason == "wind_down"` and `exit_code == 75`.
- `test_wind_down_requested_honours_new_commands_only`. The rule to test:
  - a file already in `inbox/` at `begin()` is ignored;
  - a new `{"command":"stop"}` is honoured, and so is `{"type":"wind-down"}`;
  - a new `{"type":"prompt"}` is ignored, and so is bad JSON.
- `test_request_wind_down_writes_a_command_the_reader_honours`.

`TT/test_runner.py`: update the fakes to the new signatures.
- `test_runner_wraps_the_prompt_with_the_done_marker_instruction`: the prompt that reaches the process starts
  with `"prompt"` and contains `OPENCODELOOP_TASK_FULLY_COMPLETE`.
- `test_runner_passes_bounds_and_an_inbox_probe`.
- `test_request_wind_down_rejects_an_unsafe_run_id`.

`TT/test_cli.py`
- `test_cli_exit_codes_follow_the_family`: a fake runner returns FINISHED, STOPPED and FAILED in turn → exit 0, 75 and 1.
- `test_cli_bounds_flag_beats_env_beats_default`: `env={"OPENCODELOOP_MAX_TURNS":"7"}` → 7, and `--max-turns 3` → 3.
- `test_cli_rejects_invalid_bounds_with_exit_2`: `--max-seconds 0` → 2.
- `test_cli_wind_down_writes_the_inbox_command`: an invalid run id → 2.

`TT/test_interfaces.py`: add the new domain protocols and `RunWatchdogInterface` to the tuples.

vibey, `tests/infrastructure/engines/test_opencodeloop_process.py`
- Update the expected argv at `:136-144` to end with `"--max-turns", "1"`.
- Add `test_last_response_drops_the_completion_marker_line`: the input events are `{"text":"{\"a\":1}\n"}` and
  `{"text":"OPENCODELOOP_TASK_FULLY_COMPLETE"}` → `'{"a":1}'`.

## Checks the lane must run (all must pass)
```bash
# tenant (fresh venv, exactly as the CI tools row does it; never the worktree .venv/bin shebangs)
cd src/vibey_runners/opencode
python3.12 -m venv "$TMPDIR/oc" && "$TMPDIR/oc/bin/python" -m pip install -q -e ../common -e ".[dev]"
"$TMPDIR/oc/bin/python" -m mypy --strict src/opencodeloop
"$TMPDIR/oc/bin/lint-imports"
"$TMPDIR/oc/bin/python" -m bandit -q -r src/opencodeloop
"$TMPDIR/oc/bin/python" -m pytest -q          # 100% branch floor is in addopts
cd -
# repository root
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run pytest -q -p no:cacheprovider tests/infrastructure/engines/test_opencodeloop_process.py \
  tests/infrastructure/engines/test_opencodeloop_design.py --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/engines/opencodeloop_process.py' --fail-under=100
```

## Out of scope
- Cost, tokens and `--max-dollars`. Those are Part 2.
- `--wind-down-at` deadlines, a predictive wind-down policy, and a `handoff.json` marker. vibey reads none of them today.
- Changing the OPENCODE descriptor, its effort projection or its golden files (`tests/infrastructure/engines/golden/opencode_*.txt`),
  `loop_events.py`, `classify.py`, and `src/vibey/domain/config.py`.
- The tenant README, CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and skill trees. The docs wave owns these.
- Version bumps. Do not push, open PRs or change remotes. Commit locally with the Title as the Conventional Commit subject.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network). In the tenant, `time`, `os`, `threading` and `subprocess` appear only in `infrastructure/`.
- Dependencies point inward: cli -> infrastructure -> application -> domain (the tenant's import-linter `layers` contract).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim, and `TerminalRule` encodes this.
- Code lives in classes with an interface beside each (ADR-0016). Module functions need a written reason.
- Every job is idempotent under replay: a stale inbox command from an earlier run with the same id is ignored. The ledger is append-only, so events.jsonl is only ever appended to.

---

# Part 2

Prerequisite: Part 1 is merged. It provides `RunBounds`, `StopReason`, `RunWatchdog`, `_terminate`, `RunResult.exit_code`,
the `turn.completed` counting in `OpenCodeProcess.execute`, and vibey forwarding `--max-turns`.

## Title
feat(opencodeloop): meter OpenCode token usage and cost so the budget brake can see it

## Why
The OPENCODE descriptor charges 0/0 per million tokens "until a provider-specific meter is configured"
(`src/vibey/infrastructure/engines/descriptors.py:279-284`). opencodeloop does not report any cost. It turns
OpenCode's `step_finish` into `{"event_type":"turn.completed","raw":raw}` (`T/infrastructure/opencode_process.py:186-187`),
so vibey's tail builds the payload `{"raw": {...}}` (`loop_process_adapter.py:498-505`). The one spend rule that
the budget brake and the per-engine meter share reads `payload["cost_usd"]` from `TurnCompleted`
(`src/vibey/domain/phase_timing.py:137-140`; `application/budget_source.py:12-19`; `application/engine_selection.py:251-311`).
It reads nothing here, so every OpenCode dollar goes uncounted. That matters more because OPENCODE is in `DEFAULT_DESCRIPTORS`
with `tier=EngineTier.LOCAL` (`descriptors.py:287,409`). LOCAL is preferred first (`src/vibey/domain/engine.py:51`,
`domain/rotation.py:107`), yet OpenCode can call paid providers.

OpenCode already reports usage and cost. Verified in `sst/opencode` `dev` on 2026-09-22:
- `run --format json` writes `{"type","timestamp","sessionID",...data}` (`packages/opencode/src/cli/cmd/run.ts`, `emit`).
- `step_finish` carries `part: {type:"step-finish", reason, cost: number, tokens: {total?, input, output, reasoning, cache: {read, write}}}`
  (`packages/schema/src/v1/session.ts:240-256`).
- OpenCode computes `part.cost` from each model's price. Its own per-provider, per-model config key is
  `provider.<id>.models.<id>.cost.{input,output,cache_read,cache_write}` (`packages/core/src/v1/config/provider.ts:31-45`).

So the per-provider price is configured where the provider is configured, which is OpenCode's own config.
opencodeloop only needs a **fallback** rate for a provider that has no price (`part.cost == 0` with tokens > 0).
It must never make up a price. Sub-doctrine 12.c: a rate is a key, not a constant.

## Required behaviour
1. `step_finish` (and its aliases `message_finish` and `turn_finish`) normalizes to:
   `{"event_type":"turn.completed","payload":{...},"raw":raw}`
   The `payload` holds:
   - `cost_usd` (float);
   - `cost_source`, which is one of `"opencode"`, `"configured_rate"` or `"unpriced"`;
   - `input_tokens`, `output_tokens`, `reasoning_tokens`, `cache_read_tokens` and `cache_write_tokens` (ints).

   A missing, non-numeric or `bool` value counts as 0. The `payload` envelope is the one claudeloop uses for
   its turn events (`claudeloop/application/runner.py:545-555`), and it is what both vibey readers expect:
   `loop_process_adapter.py:498-499` and `opencodeloop_process.py:151-157`.
2. **Which price wins:**
   - if `part.cost > 0`, then `cost_usd = part.cost` and `cost_source = "opencode"`;
   - else if both fallback rates are set, then
     `cost_usd = ((input + cache_read + cache_write) * price_in + (output + reasoning) * price_out) / 1_000_000`
     and `cost_source = "configured_rate"`. Cache tokens are charged at the full input rate on purpose: a brake
     that over-counts stops early, and one that under-counts spends money;
   - else `cost_usd = 0.0` and `cost_source = "unpriced"`.
3. **Fallback rate settings.**
   - `--price-in-per-mtok` / `OPENCODELOOP_PRICE_IN_PER_MTOK`
   - `--price-out-per-mtok` / `OPENCODELOOP_PRICE_OUT_PER_MTOK`

   Both default to unset. Set both or neither. Each must be ≥ 0. Anything else exits 2.
4. **Dollar cap.** `--max-dollars` / `OPENCODELOOP_MAX_DOLLARS` defaults to unset, which means no cap. When it
   is set it must be > 0. After each `turn.completed`, add up `cost_usd`. When the running total is
   `>= max_dollars`, `watchdog.trip(StopReason.MAX_DOLLARS)` and then `_terminate(process)`. The run's status is
   FAILED, with detail `stopped at bound: max_dollars` and exit 1. That matches the family rule that running out
   of budget is exit 1 (`claudeloop/cli/outcome.py:10`).
5. `RunResult` also carries the run's totals: `turns`, `cost_usd`, `input_tokens` and `output_tokens`. `finish()` writes
   them into `meta.json` and `snapshots/latest.json`.
6. **vibey DESIGN path:** `OpenCodeLoopProcess.run` also adds `"--max-dollars", format(self._max_dollars, "g")`.
   This copies `claudeloop_process.py:93-103`.
7. **vibey BUILD path:** no production code changes. A new test proves that an opencodeloop `turn.completed` line
   reaches the ledger as a `TurnCompleted` with the same `cost_usd`, and that `LEDGER_SPEND_RULE` charges it.
8. **Descriptor comment.** In `descriptors.py:279-282`, rewrite the comment to say that the meter is the
   per-turn `cost_usd` that opencodeloop reports. The descriptor's `cost_per_mtok_*` values stay `0.0`,
   because they are only a rotation weighting hint (`domain/rotation.py:143`) and not the meter. Change no values.

## Where to change
Tenant, domain: `T/domain/model.py`
```python
class StopReason(StrEnum): ...; MAX_DOLLARS = "max_dollars"      # add the member
@dataclass(frozen=True, slots=True)
class RunBounds: ...; max_dollars: float | None = None           # validate: None or > 0

@dataclass(frozen=True, slots=True)
class TurnUsage:
    reported_cost: float = 0.0
    input_tokens: int = 0; output_tokens: int = 0; reasoning_tokens: int = 0
    cache_read_tokens: int = 0; cache_write_tokens: int = 0
    @classmethod
    def from_step(cls, part: Mapping[str, object]) -> "TurnUsage": ...   # pure parse of part.cost / part.tokens

@dataclass(frozen=True, slots=True)
class UsagePricing:
    price_in_per_mtok: float | None = None
    price_out_per_mtok: float | None = None
    # __post_init__: both-or-neither, each >= 0, else ValueError
    def price(self, usage: TurnUsage) -> tuple[float, str]: ...          # rule in item 2
```
- Add `turns`, `cost_usd`, `input_tokens` and `output_tokens` to `RunResult` as trailing fields that default to zero.
- Add `TurnUsageInterface` and `UsagePricingInterface` to `T/domain/interfaces/model_interface.py`, and add
  the new `RunResult` properties to `RunResultInterface`.

Tenant, infrastructure: `T/infrastructure/opencode_process.py`
- `_normalize(cls, line, pricing: UsagePricing | None = None)`. The `_STEP_FINISH` branch (`:186-187`) returns
  `{"event_type":"turn.completed","payload":cls._usage_payload(raw, pricing or UsagePricing()),"raw":raw}`.
- `_usage_payload(raw, pricing)` reads `raw["part"]` only when it is a mapping. It builds a `TurnUsage` and prices it.
- `execute(...)` gains `pricing: UsagePricing`. It passes `pricing` to `_normalize` and totals turns, cost and
  tokens from each `turn.completed` payload. If `bounds.max_dollars` is set and the cost total is `>= max_dollars`,
  it trips `MAX_DOLLARS` and calls `_terminate`. It returns the totals in `RunResult`.
- Update `T/application/interfaces/process_interface.py`.

Tenant, application: `T/application/runner.py`. `run(..., pricing: UsagePricing = UsagePricing())` passes it
through. Mirror this in `runner_interface.py`.

Tenant, store: `T/infrastructure/run_store.py`. In `finish()`, add `turns`, `cost_usd`, `input_tokens` and
`output_tokens` to `metadata`.

Tenant, CLI: `T/cli/app.py`. Add `--max-dollars`, `--price-in-per-mtok` and `--price-out-per-mtok`, each with
`envvar=`, to `run` and `resume`. Build `RunBounds(..., max_dollars=...)` and `UsagePricing(...)` inside the
existing `try` blocks.

vibey:
- `src/vibey/infrastructure/engines/opencodeloop_process.py:84` (as Part 1 left it): append
  `"--max-dollars", format(self._max_dollars, "g")`.
- `src/vibey/infrastructure/engines/descriptors.py:279-282`: rewrite the comment only.

## Acceptance criteria
- [ ] The tenant suite passes at 100% branch coverage. `mypy --strict`, `lint-imports` and `bandit` pass.
- [ ] A `step_finish` with `part.cost = 0.0123` normalizes to `payload.cost_usd == 0.0123` and `cost_source == "opencode"`.
- [ ] `part.cost = 0` with tokens and rates of 3.0 in / 15.0 out → `configured_rate` at the computed value.
      With no rates → `0.0` and `"unpriced"`.
- [ ] `--max-dollars 0.05` stops a run whose second turn brings the total to ≥ 0.05. The result is `exit_code == 1`
      and `stop_reason == "max_dollars"`.
- [ ] vibey: `uv run pytest -q -p no:cacheprovider tests/infrastructure/engines/test_loop_process_adapter.py tests/infrastructure/engines/test_opencodeloop_process.py` passes.

## Tests to write first (TDD)
`TT/test_model.py`
- `test_turn_usage_from_step_reads_cost_and_every_token_field`.
- `test_turn_usage_from_step_zeroes_missing_bool_and_non_numeric_fields`.
- `test_usage_pricing_prefers_opencode_reported_cost`.
- `test_usage_pricing_falls_back_to_configured_rates`: input 1000, cache_read 500, output 200, reasoning 100,
  at rates 3.0/15.0 → `(1500*3 + 300*15)/1e6 = 0.009`.
- `test_usage_pricing_marks_unpriced_usage`.
- `test_usage_pricing_requires_both_rates_or_neither_and_non_negative`.
- `test_run_bounds_rejects_non_positive_max_dollars`.

`TT/test_process.py`
- `test_normalize_step_finish_carries_usage_in_a_payload_envelope`.
- `test_execute_totals_turn_usage_into_the_result`.
- `test_execute_stops_at_the_dollar_cap`: fake `killpg` gets SIGTERM, `stop_reason is MAX_DOLLARS`, and exit 1.
- `test_execute_without_a_dollar_cap_never_trips_on_cost`.

`TT/test_store.py`
- `test_finish_records_usage_totals`.

`TT/test_cli.py`
- `test_cli_prices_come_from_flags_or_env`.
- `test_cli_rejects_one_rate_without_the_other_with_exit_2`.
- `test_cli_rejects_non_positive_max_dollars_with_exit_2`.

vibey, `tests/infrastructure/engines/test_loop_process_adapter.py`
- `test_tail_carries_opencodeloop_turn_cost_to_the_spend_rule`:
  - use `LoopProcessAdapter(descriptor=OPENCODE)` and the `_make_handle` helper (`:29-35`);
  - write `events.jsonl` containing
    `{"timestamp":"2026-01-01T00:00:00+00:00","event_type":"turn.completed","payload":{"cost_usd":0.0123,"cost_source":"opencode","input_tokens":1000,"output_tokens":200},"raw":{"type":"step_finish"}}`;
  - write `meta.json` with `{"status":"finished"}`;
  - assert: the event's kind is `"TurnCompleted"`; `payload["cost_usd"] == 0.0123`; and
    `LEDGER_SPEND_RULE.spend_of_payload(kind, payload).dollars == 0.0123`, where `LEDGER_SPEND_RULE` comes from `vibey.domain.phase_timing`.

vibey, `tests/infrastructure/engines/test_opencodeloop_process.py`
- Extend the argv assertion so it ends with `"--max-turns", "1", "--max-dollars", "0.25"`.

## Checks the lane must run (all must pass)
Run the same commands as in Part 1, and add
`tests/infrastructure/engines/test_loop_process_adapter.py` to the focused `uv run pytest` line. Also run
`uv run coverage report --include='src/vibey/infrastructure/engines/opencodeloop_process.py' --fail-under=100`.

## Out of scope
- The OPENCODE descriptor's `tier` (LOCAL, although OpenCode can bill a paid provider), its `cost_per_mtok_*` values,
  and `src/vibey/domain/config.py`. Changing them is a rotation-policy decision for another issue.
- A rate table per provider inside opencodeloop. The run's JSON stream does not say which provider served a step,
  and OpenCode's own `provider.*.models.*.cost` already does per-provider pricing.
- The tenant README. Its line "billing settings remain outside this package" (`src/vibey_runners/opencode/README.md:11-13`) goes
  stale with this part, so pass it to the docs wave. Also out of scope: CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md, skill trees, and version bumps. Do not push, open PRs or change remotes. Commit locally
  with the Title as the Conventional Commit subject.

## Hard repository rules (always)
- domain/ stays pure. `TurnUsage.from_step` and `UsagePricing.price` are pure arithmetic over mappings.
- Dependencies point inward (the import-linter layers contract, in the tenant and in vibey).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim, and Part 1's `TerminalRule` stays as it is.
- Code lives in classes with an interface beside each (ADR-0016). Module functions need a written reason.
- Every job is idempotent under replay, and the ledger is append-only. Cost is recorded only on the turn events
  the run writes, never added up again on a reused result (`opencodeloop_process.py:80-82` returns a reused result
  without calling `_record`; keep it that way).
