## Title
test(fakes): a clock you can move, a logger, a notification sink and telemetry you can read back

## Why
`Clock` (`application/interfaces/system.py:11-12`) and the five observability ports
(`application/interfaces/observability.py:23-120`: `Logger`, `NotificationSink`,
`TelemetrySpan`, `TelemetryTracer`, `TelemetryMetrics`) have no shared fake. The same
doubles are rewritten by hand:
- `FakeClock` in `tests/application/test_deploy_design_and_acceptance.py` and in
  `tests/application/test_deploy_execute_handler.py:37-39`;
- `_RecordingLogger` in `tests/application/test_worker.py:639-`;
- `_RecordingNotifications` in `tests/application/test_worker.py:51-57`.

The telemetry ports are faked nowhere. Code that takes a tracer is tested either against the
real OpenTelemetry-backed classes, or not at all. `fakes-registry` lists all six ports as
`PENDING` under this lane.

## Required behaviour
1. **`tests/fakes/system.py` — `class FakeClock`** (implements `Clock`):
   - `__init__(self, start: datetime = datetime(2026, 1, 1, tzinfo=UTC))`. A naive
     `start` raises `ValueError`;
   - `now()` returns the current instant;
   - `advance(self, delta: timedelta) -> datetime` moves the instant forward. A negative
     `delta` raises `ValueError("a clock does not run backwards")`;
   - `set(self, instant: datetime) -> None`, under the same aware and monotonic rules.
2. **`tests/fakes/observability.py`**:
   - **`RecordingLogger`** (implements `Logger`). `lines: list[LogLine]`, where
     `LogLine` is a frozen dataclass of `level`, `event`, `fields` and `bound`.
     `bind(**kw)` returns a **new** `RecordingLogger` that shares the same `lines` list and
     has `bound` merged. Each level appends a `LogLine`, whose `fields` is the call's
     kwargs. A helper `events(level=None) -> list[str]` returns the events in order.
   - **`RecordingNotificationSink`** (implements `NotificationSink`). `notify(...)` appends
     a frozen `Notification` with all six fields to `self.sent`. It returns
     `{"enabled": True, "desktop": False, "webhooks": []}`, or `{"enabled": False}` when it
     was constructed with `enabled=False`, in which case it records nothing.
   - **`RecordedSpan`** (implements `TelemetrySpan`). It has `name`, `attributes: dict` and
     `events: list[tuple[str, dict]]`, and `set_attribute` and `add_event` write to them.
   - **`InMemoryTelemetryTracer`** (implements `TelemetryTracer`). Each `trace_*` is a
     `contextlib.contextmanager`. It creates a `RecordedSpan` named `job`, `turn` or
     `handoff`, pre-filled with the call's keyword arguments as attributes, with enum values
     stored as `.value`. It appends the span to `self.spans` and yields it. If the body
     raises, it records `add_event("exception", {"type": type(exc).__name__})` and re-raises.
   - **`InMemoryTelemetryMetrics`** (implements `TelemetryMetrics`). Each `record_*`
     appends `(method_name, kwargs)` to `self.records`, with the positional arguments
     named as in the port. A helper `values(name) -> list[dict[str, object]]` returns them.
3. **Registry.** Register all six, and delete their `PENDING` lines.
4. **Switch the tests:**
   - delete `FakeClock` from the two deploy test modules and import it from `tests.fakes.system`.
     Where a test relied on a fixed `NOW`, construct `FakeClock(NOW)`;
   - delete `_RecordingLogger` and `_RecordingNotifications` from `tests/application/test_worker.py`
     and use the shared classes, asserting on `lines` and `sent` as the old tests asserted on
     theirs.

## Where to change
- New `tests/fakes/system.py`, `tests/fakes/observability.py` and
  `tests/fakes/test_fake_observability.py`.
- `tests/fakes/registry.py`, `tests/application/test_worker.py`,
  `tests/application/test_deploy_design_and_acceptance.py`,
  `tests/application/test_deploy_execute_handler.py`.

## Acceptance criteria
- [ ] `grep -rn "class FakeClock\|class _RecordingLogger\|class _RecordingNotifications" tests/application` prints nothing.
- [ ] The registry has no `PENDING` entry naming `fakes-observability`.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application tests/fakes` passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_observability.py`:
- `test_clock_advances_and_refuses_to_go_backwards`
- `test_clock_refuses_a_naive_instant`
- `test_bound_logger_shares_lines_and_merges_context`
- `test_sink_records_every_field_and_can_be_disabled`
- `test_tracer_records_attributes_and_the_exception_event`
- `test_metrics_record_named_arguments`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The production OpenTelemetry classes and their tests (`tests/infrastructure/test_otel.py`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected tests.
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
See STORM/SPEC-TEMPLATE.md.
