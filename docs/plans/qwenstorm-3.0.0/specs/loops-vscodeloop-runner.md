## Title
feat(vscodeloop): the session runner — bounds, watchdog, inbox and the terminal rule, behind an editor-driver port

ADR-0046 lane L20f (slug `loops-vscodeloop-runner`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:265-285`): vscodeloop follows the family contract, its
bounds and terminal rule are the dropped parity spec's, and "the editor driver sits behind a
port" so that the Code - OSS driver (lane `loops-vscodeloop-oss-driver`, gated on the V-VS
evidence) is one implementation of it. This lane builds everything a run needs except the
real editor: the port, a scripted in-memory fake, and the runner that turns a driver's session
into the family's `events.jsonl` and exit codes.

The rules are carried from `specs/opencodeloop-parity-p1.md` (behaviours 1, 3–10): wrap the
prompt with the family's `with_done_marker_instruction`
(`src/vibey_runners/common/src/vibey_runners/common/application/usecases/completion.py:28`,
integration `d3b4a388`; sub-doctrine 10.e: use it, do not copy it); read the completion claim
from the **last** assistant text only; turn cap on `turn.starting`; a watchdog for wall time,
stall and wind-down with the first trip winning; the terminal rule with capacity first.
Non-negotiable 3: a capacity rejection outranks a completion claim.

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. **The port** — `vscodeloop/application/interfaces/editor_driver.py`:
   ```python
   @dataclass(frozen=True, slots=True)
   class DriverSettings:
       editor: str                 # the editor binary (VSCODELOOP_EDITOR), resolved by the CLI
       model: str                  # the model the session must use
       base_url: str | None        # local OpenAI-compatible endpoint (sovereign mode)
       provider: str | None        # the paid provider (paid mode, `--paid`)

   @dataclass(frozen=True, slots=True)
   class DriverEvent:
       kind: str                   # one of DRIVER_EVENT_KINDS
       text: str | None = None
       payload: Mapping[str, object] = field(default_factory=dict)

   DRIVER_EVENT_KINDS = frozenset({"turn.starting", "turn.completed", "text", "tool", "capacity", "error"})

   @runtime_checkable
   class DriverSessionInterface(Protocol):
       @property
       def session_id(self) -> str: ...

   @runtime_checkable
   class EditorDriverInterface(Protocol):
       def start(self, *, workdir: Path, prompt: str, settings: DriverSettings,
                 session_id: str | None) -> DriverSessionInterface: ...
       def events(self, session: DriverSessionInterface) -> Iterator[DriverEvent]: ...
       def send(self, session: DriverSessionInterface, text: str) -> None: ...
       def stop(self, session: DriverSessionInterface) -> None: ...
   ```
   `events()` blocks and ends when the session ends (or after `stop`). `capacity` events carry
   `payload["state"]` in `credits_exhausted | window_exhausted | auth_failed` (+ optional
   `resets_at` for a window, never for credits); `error` events carry `payload["misconfigured"]: bool`.
   Export from `application/interfaces/__init__.py` with `RunStoreInterface`.
2. **The fake** — `src/vibey_runners/vscode/tests/fakes.py` (test support, not shipped):
   `class FakeEditorDriver` implementing the port with real behaviour: constructed with a
   scripted `list[DriverEvent]` and an optional `on_event: Callable[[DriverEvent], None]`
   (tests use it to advance a fake clock); records `starts`, `sent`, `stopped`; `events()`
   yields the script and stops early once `stop()` was called. `FakeSession(session_id="s-1")`.
3. **The runner** — `vscodeloop/application/runner.py`:
   ```python
   class RunWatchdog:
       def __init__(self, bounds: RunBounds, *, clock: Callable[[], float],
                    wind_down_requested: Callable[[], bool]) -> None
       reason: StopReason | None            # property
       def touch(self) -> None               # last activity = clock()
       def trip(self, reason: StopReason) -> bool   # under a threading.Lock; first trip wins
       def check(self) -> StopReason | None  # returns the reason only when THIS call tripped it;
                                             # order: WIND_DOWN, MAX_SECONDS, STALL_TIMEOUT

   class SessionRunner:
       def __init__(self, driver: EditorDriverInterface, store: RunStoreInterface, *,
                    clock: Callable[[], float] = time.monotonic, poll_seconds: float = 1.0) -> None
       def run(self, *, prompt: str, run_id: str, cwd: Path, bounds: RunBounds,
               settings: DriverSettings, session_id: str | None = None) -> RunResult
   ```
   `run` does, in order:
   1. `run_dir = store.run_dir(cwd, run_id)`; `store.begin(run_dir, run_id=…, cwd=cwd, session_id=session_id)`.
   2. `session = driver.start(workdir=cwd, prompt=with_done_marker_instruction(prompt, DONE_MARKER), settings=settings, session_id=session_id)`;
      append `{"event_type": "run.started", "session_id": session.session_id}`.
      A driver exception here → misconfigured if it is `DriverMisconfigured` (a new exception
      class in the port module, subclass of `RuntimeError`), else driver_failed; skip to step 5.
   3. Start a daemon thread: every `poll_seconds`, if `watchdog.check()` trips → `driver.stop(session)`;
      deliver new inbox commands (`store.new_commands`): `prompt-now` → `driver.send` now;
      `prompt-at-break` → queued until the next `turn.completed`; `stop`/`wind_down` are seen
      by `wind_down_requested` (the watchdog's callable is `lambda: store.wind_down_requested(run_dir)`).
   4. For each driver event (and `watchdog.touch()` + `watchdog.check()` after each one):
      - `turn.starting`: if `turns >= bounds.max_turns` and `watchdog.trip(StopReason.MAX_TURNS)` →
        `driver.stop(session)`; else append `{"event_type": "turn.starting"}`;
      - `turn.completed`: `turns += 1`; append `{"event_type": "turn.completed", "turn": turns}`; send queued at-break prompts;
      - `text`: remember as `last_text`; append `{"event_type": "text_delta", "text": text}`;
      - `tool`: append `{"event_type": "tool_result", **payload}`;
      - `capacity`: `capacity_rejected = True`; append
        `{"event_type": "capacity.rejected", "capacity": {"state": payload["state"], **({"resets_at": …} if a window)}}`
        (the family shape `_classify_claudeloop` reads, lane `loops-vscode-engine-ids`);
      - `error`: set `misconfigured` or `driver_failed` from `payload["misconfigured"]`;
        append `{"event_type": "error", "detail": text}`.
   5. `status = TerminalRule().decide(capacity_rejected=…, stop_reason=watchdog.reason, misconfigured=…, driver_failed=…, completion_claimed=CompletionMarker().claimed_by(last_text or ""))`;
      `detail` in this order: capacity → `"the provider reported a capacity rejection"`;
      wind-down → `"wound down on request"`; a bound → `"stopped at bound: <reason.value>"`;
      misconfigured → the error text or `"backend misconfigured"`; driver failure → the error
      text; no claim → `"session ended without the completion marker"`.
   6. Append the terminal event: FINISHED → `{"event_type": "finished", "success": True, "session_id": …}`;
      else `{"event_type": "failed", "success": False, "detail": …, "stop_reason": …, "session_id": …}`.
   7. `store.finish(run_dir, result)`; join the thread; return `RunResult(status, session_id, detail, watchdog.reason, misconfigured)`.
4. `vscodeloop/application/interfaces/runner_interface.py`: `RunWatchdogInterface`,
   `SessionRunnerInterface` Protocols; export them.

## Where to change
- New: `vscodeloop/application/interfaces/editor_driver.py`, `.../interfaces/runner_interface.py`,
  `vscodeloop/application/runner.py`; `tests/fakes.py`; `tests/test_runner.py` (provenance
  line 1 on each, copied from `tests/test_domain.py`).

## Acceptance criteria
- [ ] A scripted session that ends with the marker in its last text finishes: exit 0, terminal event `finished`, `meta.json` status `finished`.
- [ ] The marker in an earlier text but not the last does not count (FAILED, "session ended without the completion marker").
- [ ] A `capacity` event plus a marker → FAILED, and `events.jsonl` holds `capacity.rejected` with `{"capacity": {"state": "credits_exhausted"}}` and no `resets_at`.
- [ ] A `stop` written to the inbox mid-run → STOPPED, exit 75, `driver.stop` called once.
- [ ] `max_turns=2` and a third `turn.starting` → FAILED with stop reason `max_turns`; exactly `max_turns` turns still finish.
- [ ] A stall (fake clock advanced past `stall_timeout_seconds` with no event) → FAILED `stall_timeout`.
- [ ] `DriverMisconfigured` at start → FAILED, `exit_code == 78`.
- [ ] `prompt-now` is sent immediately; `prompt-at-break` after the next `turn.completed`.
- [ ] The prompt the driver received ends with the family's done-marker instruction.
- [ ] Tenant suite at 100% branch coverage; mypy strict, lint-imports, bandit pass.

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_runner.py` (with `FakeEditorDriver`, the real `FileRunStore`
on `tmp_path`, a `_Clock` object passed as `clock=lambda: c.now`, `poll_seconds=0.01`):
- `test_watchdog_checks_in_order_and_first_trip_wins`
- `test_finishes_on_a_marker_in_the_last_text`
- `test_marker_in_an_earlier_text_does_not_count`
- `test_capacity_rejection_outranks_a_marker`
- `test_inbox_stop_winds_down_with_exit_75`
- `test_turn_cap_trips_on_the_next_turn_starting`
- `test_exactly_max_turns_still_finishes`
- `test_stall_timeout_trips`
- `test_max_seconds_trips`
- `test_misconfigured_driver_exits_78`
- `test_driver_failure_is_a_failed_run`
- `test_prompts_are_delivered_now_and_at_break`
- `test_prompt_carries_the_done_marker_instruction`
- `test_runner_and_watchdog_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The real Code - OSS driver (`loops-vscodeloop-oss-driver`), the CLI (`loops-vscodeloop-cli`),
  the doctor (`loops-vscodeloop-doctor`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscodeloop-run-store`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
