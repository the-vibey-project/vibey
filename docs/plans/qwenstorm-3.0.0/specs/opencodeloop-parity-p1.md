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

## Context shared by every part of this work
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
