<!-- split of #367: child 1 of 2; audit: issue-audit/updates/367.md -->

## Title
refactor(engines): extract the run-directory tailer, the inbox writer and the stop-summary reader from LoopProcessAdapter

## Why
ADR-0044 §13–§14 (`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:434`, `:449`, `:541`) extracts the run-directory machinery from `LoopProcessAdapter` into `infrastructure/engines/run_dir.py`, with no behaviour change. Draft ADR-0046 (`STORM/specs/ADR-two-loops.md`) replaces ADR-0044's one-service-per-engine design but keeps this extraction: "The inbox and tailer are R20's extracted classes" (line 339). Their consumers will be ADR-0046's **seat host**, which writes control commands into a running runner's inbox, and its caller-side **adapter** (`infrastructure/loop_service/adapter.py`, §10 line 304), which tails `events.jsonl` on the shared volume. Those lanes are not written yet; this lane only prepares the classes they will use.

The machinery lives today in `src/vibey/infrastructure/engines/loop_process_adapter.py` (738 lines; every anchor below verified at the storm integration branch `4317cff6`, unchanged since the audit at `739536ea`):
- tailing `events.jsonl` into `EngineEvent`s: `tail`, `:418-589` (body `:425-589`), including the "process exited without a terminal status" check at `:567-580`;
- writing inbox commands: `send_prompt`, `:591-614`, and the stop file in `stop`, `:653-657`;
- waiting for and reading `stop-summary.md`: `:659-673`.

Duplicating it would break sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`). Sub-doctrine 9.b (`doctrines.md:349`) requires classes with an interface beside each. **The adapter's behaviour does not change.**

## Required behaviour
1. **`src/vibey/infrastructure/engines/run_dir.py`** holds exactly three classes, and `__all__ = ["RunDirTailer", "RunInbox", "StopSummaryReader"]`.
   - `class RunDirTailer`, built as `RunDirTailer(descriptor: EngineDescriptor)`. It stores the descriptor and exposes it as a read-only property `descriptor`. Its method is
     `async def tail(self, run_dir: Path, *, run_id: object, process_exit_code: Callable[[], int | None]) -> AsyncIterator[EngineEvent]`.
     - Its body is `LoopProcessAdapter.tail`'s body (`:425-589`) moved verbatim, with `handle.run_dir` → `run_dir` and `handle.run_id` → `run_id`. `self.descriptor` keeps working through the property.
     - The `_active_processes` check (`:567-580`) becomes `returncode = process_exit_code()`. When it is not `None`, the same one-poll grace applies (break once more than 1.0 s has passed since the exit was first seen), and the same `process_exited_without_terminal_status` warning is logged with `run_id=str(run_id)` and `returncode=returncode`. When it is `None`, the grace timer resets to `None`, as today.
     - (The original R20 used `process_exited: Callable[[], bool]`; the callable returns the exit code instead, so that the warning keeps its `returncode` field byte for byte.)
   - `class RunInbox`, built as `RunInbox(run_dir: Path)`:
     - `write_prompt(self, text: str, *, now: bool) -> Path` does what `:593-605` does: it creates `run_dir / "inbox"` with `parents=True, exist_ok=True`, and writes `<ts>-prompt-now.json` (when `now`) or `<ts>-prompt-at-break.json` holding `json.dumps({"command": "prompt-now" | "prompt-at-break", "text": text})`, where `<ts>` is `datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")`. It returns the path it wrote.
     - `write_command(self, command: str) -> Path` creates the inbox the same way and writes `<ts>-<command>.json` holding `json.dumps({"command": command})`. It returns the path.
     - `write_stop(self) -> Path` returns `self.write_command("stop")`, which is exactly the file `:653-657` writes today.
   - `class StopSummaryReader`, built as `StopSummaryReader(descriptor: EngineDescriptor)`, with
     `async def read(self, run_dir: Path, *, wait_seconds: float = 30.0) -> tuple[str, bool]`.
     It does what `:659-673` does: it polls every 0.5 s, at most `int(wait_seconds / 0.5)` times (60 by default), until `run_dir / "stop-summary.md"` exists and is non-empty. Then, if the file exists, it returns `(text, descriptor.done_marker in text)`; if it does not exist, it returns `("", False)`.
2. **`LoopProcessAdapter` delegates** to these classes, building each one per call:
   - `tail` keeps its signature and docstring. Its body becomes:
     ```python
     tailer = RunDirTailer(self.descriptor)
     async for event in tailer.tail(
         handle.run_dir,
         run_id=handle.run_id,
         process_exit_code=lambda: self.run_exit_code(handle),
     ):
         yield event
     ```
     `run_exit_code` (`:616-623`) already returns `_active_processes[handle.run_id].returncode` when that process is registered, else `None`, which is exactly the old check.
   - `send_prompt` keeps its signature and docstring. Its body becomes `prompt_file = RunInbox(handle.run_dir).write_prompt(text, now=now)`, followed by the unchanged `logger.info("prompt_sent", run_id=str(handle.run_id), now=now, file=str(prompt_file))` of `:609-614`.
   - `stop` keeps its signature and docstring. Lines `:653-673` (the stop file, the summary wait and the summary read) become:
     ```python
     RunInbox(handle.run_dir).write_stop()
     summary, complete = await StopSummaryReader(self.descriptor).read(handle.run_dir)
     remaining_work: list[str] = []
     ```
     Everything from `# Try to get remaining work from final snapshot` (`:675`) to the end of `stop` (`:706`) is unchanged.
3. **Everything else stays in `loop_process_adapter.py`**, with the same names and signatures: `_active_processes`, `_diagnostic_files`, `_help_text_cache`, `_ANSI_ESCAPE`, `isolate_python_env`, `ProcessError`, `_render_plan`, `_spawn`, `_communicate`, `_engine_environment`, and every public method. `__all__` (`:738`) is unchanged. No dataclass field is added to `LoopProcessAdapter`.
4. **Behaviour is byte-identical**: the same log event names and keyword fields (`events_file_missing`, `event_missing_type`, `unknown_event_type`, `event_parse_failed`, `process_exited_without_terminal_status`, `tail_error`, `prompt_sent`), the same file names and JSON bodies, and the same poll intervals and bounds (100 × 0.1 s for `events.jsonl` to appear, a 0.5 s tail poll, 60 × 0.5 s for the summary). The one visible difference is structlog's `logger` name field (added by `structlog.stdlib.add_logger_name`, `src/vibey/infrastructure/logging.py:79`) on the moved tail events: it becomes `vibey.infrastructure.engines.run_dir`. Use `logger = structlog.get_logger(__name__)` in `run_dir.py`.
5. The three classes satisfy `@runtime_checkable` Protocols `RunDirTailerInterface`, `RunInboxInterface` and `StopSummaryReaderInterface`.

## Where to change
- **New `src/vibey/infrastructure/engines/run_dir.py`.**
  - Line 1 is the provenance comment, copied byte for byte from line 1 of `loop_process_adapter.py`. It reads: `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Then a module docstring saying these are the run-directory classes extracted from `LoopProcessAdapter` (ADR-0044 §13, ADR-0046 §10), declared by `interfaces/run_dir_interface.py`.
  - Imports it needs: `asyncio`, `json`, `from collections.abc import AsyncIterator, Callable`, `from datetime import UTC, datetime`, `from pathlib import Path`, `structlog`, `from vibey.application.dto import EngineEvent`, `from vibey.domain.engine import EngineDescriptor`, `from vibey.domain.ledger import EventKind`, `from vibey.infrastructure.engines.loop_events import translate_event_type`.
  - Copy the tail body from `loop_process_adapter.py:425-589` with `read_file`, then apply exactly the substitutions in behaviour 1. The replacement for `:567-580` is:
    ```python
                    returncode = process_exit_code()
                    if returncode is not None:
                        now = asyncio.get_running_loop().time()
                        if process_exited_without_status_since is None:
                            process_exited_without_status_since = now
                        elif now - process_exited_without_status_since > 1.0:
                            logger.warning(
                                "process_exited_without_terminal_status",
                                run_id=str(run_id),
                                returncode=returncode,
                            )
                            break
                    else:
                        process_exited_without_status_since = None
    ```
    Keep every comment of the moved body.
- **New `src/vibey/infrastructure/engines/interfaces/run_dir_interface.py`.** Same provenance line 1. Copy the style of `src/vibey/infrastructure/engines/interfaces/local_engines_interface.py` (module docstring "Mirrors `vibey/infrastructure/engines/run_dir.py` (ADR-0016). Interfaces declare; they never consume."). It declares:
  - `RunDirTailerInterface`: a `descriptor` property returning `EngineDescriptor`, and `def tail(self, run_dir: Path, *, run_id: object, process_exit_code: Callable[[], int | None]) -> AsyncIterator[EngineEvent]: ...` (a plain `def`, as `EngineAdapter.tail` is declared in `src/vibey/application/interfaces/engines.py:60`).
  - `RunInboxInterface`: `write_prompt(self, text: str, *, now: bool) -> Path`, `write_command(self, command: str) -> Path`, `write_stop(self) -> Path`.
  - `StopSummaryReaderInterface`: `async def read(self, run_dir: Path, *, wait_seconds: float = 30.0) -> tuple[str, bool]`.
  Each is decorated `@runtime_checkable`. This package is already in `.importlinter`'s `infrastructure-interfaces-declare-only` contract (`.importlinter:108-133`, its entry at `:115`), so `.importlinter` does not change. Do not edit `interfaces/__init__.py`.
- **`src/vibey/infrastructure/engines/loop_process_adapter.py`** (738 lines: use `edit_file` only, never `write_file`):
  - Add `from vibey.infrastructure.engines.run_dir import RunDirTailer, RunInbox, StopSummaryReader`.
  - Replace the three bodies as behaviour 2 says.
  - Remove the imports that become unused: `from datetime import UTC, datetime` (`:23`), `from vibey.domain.ledger import EventKind` (`:41`) and `from vibey.infrastructure.engines.loop_events import translate_event_type` (`:44`). `json`, `asyncio`, `AsyncIterator` and `EngineEvent` stay in use.
  - Then run `uv run ruff check --fix src/vibey/infrastructure/engines/loop_process_adapter.py src/vibey/infrastructure/engines/run_dir.py` and `uv run ruff format` on the same files, so the import order passes.
- **Do not confuse this with `src/vibey/infrastructure/engines/tailer.py`**, which turns `EngineEvent`s into `LedgerEventDraft`s. It is a different job, and it is not edited.
- **New `tests/infrastructure/engines/test_run_dir.py`** (same provenance line 1).

## Acceptance criteria
- [ ] `tests/infrastructure/engines/test_loop_process_adapter.py` passes **with no edits** (`git diff --stat HEAD~1 -- tests/infrastructure/engines/test_loop_process_adapter.py` prints nothing after the commit).
- [ ] `tests/infrastructure/process/test_call_sites.py` (including `test_the_reaper_does_not_change_how_adapters_compare`), `tests/infrastructure/test_gate_runner.py`, `tests/application/test_conformance.py` and `tests/live` pass unedited.
- [ ] `tests/application/test_interfaces_convention.py::test_infrastructure_protocols_are_declared_in_its_own_interfaces` passes (no Protocol is declared in `run_dir.py`).
- [ ] The three new classes have the direct unit tests listed below. Those tests use `tmp_path` and injected callables only: no `monkeypatch.setattr`, no `mock.patch`, no `MagicMock`/`AsyncMock`. If `tests/meta/patching_baseline.json` exists (lane `fakes-registry`), it does not change.
- [ ] `isinstance` holds for each class against its interface (`test_classes_satisfy_their_interfaces`).
- [ ] `grep -n "translate_event_type\|stop-summary.md\|prompt-at-break" src/vibey/infrastructure/engines/loop_process_adapter.py` prints nothing.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_run_dir.py`. Every test finishes in under 5 s, so every tailer test writes `events.jsonl` before tailing (a missing file waits 10 s; that branch stays covered by the unedited adapter tests).
- `test_tailer_translates_and_stops_on_terminal_meta`: with `RunDirTailer(CODEXLOOP)` (`from vibey.infrastructure.engines.descriptors import CODEXLOOP`), write two `events.jsonl` lines — `{"event_type": "turn.started", "payload": {"n": 1}}` and the flat codexloop shape `{"type": "thread.started", "thread_id": "t-1"}` — and `meta.json` holding `{"status": "finished"}`, all before tailing with `process_exit_code=lambda: None`. It yields `[EventKind.TURN_REQUESTED.value, EventKind.SESSION_SEEDED.value]` with payloads `{"n": 1}` and `{"thread_id": "t-1"}`, then ends.
- `test_tailer_enriches_a_successful_verdict_with_the_done_marker`: with `RunDirTailer(CLAUDELOOP)`, the line `{"event_type": "finished", "payload": {"success": true}}` and a finished `meta.json` yield one `EventKind.VERDICT_RENDERED.value` event whose payload has `done_marker == CLAUDELOOP.done_marker` and `complete is True`.
- `test_tailer_stops_after_the_process_exits_without_status`: an empty `events.jsonl`, no `meta.json`, and `process_exit_code=lambda: 1`. The tail ends on its own (after the one-poll grace, about 1.5 s), yields nothing, and `structlog.testing.capture_logs()` records one `process_exited_without_terminal_status` entry with `returncode == 1`.
- `test_inbox_writes_prompt_stop_and_command_files`: call `write_prompt("a", now=True)`, `write_prompt("b", now=False)`, `write_stop()` and `write_command("wind_down")` on `RunInbox(tmp_path / "run")` (the directory does not exist yet). Each returned path exists, and `glob` finds exactly one each of `inbox/*-prompt-now.json`, `*-prompt-at-break.json`, `*-stop.json` and `*-wind_down.json`, with the JSON bodies `{"command": "prompt-now", "text": "a"}`, `{"command": "prompt-at-break", "text": "b"}`, `{"command": "stop"}` and `{"command": "wind_down"}`.
- `test_stop_summary_reader_detects_the_marker`: a `stop-summary.md` that contains `CLAUDELOOP.done_marker` gives `(text, True)`; one without it gives `(text, False)`.
- `test_stop_summary_reader_gives_up_when_no_summary_appears`: with `wait_seconds=0.5` and no file, it returns `("", False)`.
- `test_classes_satisfy_their_interfaces`: `isinstance(RunDirTailer(CLAUDELOOP), RunDirTailerInterface)`, `isinstance(RunInbox(tmp_path), RunInboxInterface)`, `isinstance(StopSummaryReader(CLAUDELOOP), StopSummaryReaderInterface)`, and `RunDirTailer(CLAUDELOOP).descriptor is CLAUDELOOP`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/process tests/infrastructure/test_gate_runner.py tests/application/test_conformance.py tests/application/test_interfaces_convention.py tests/live
uv run pytest -q -p no:cacheprovider tests/system/test_full_worker_faked.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# after the local commit, this must print nothing:
git diff --stat HEAD~1 -- tests/infrastructure/engines/test_loop_process_adapter.py tests/live
```
`tests/system/test_full_worker_faked.py` needs PostgreSQL today (the root `tests/conftest.py` opens it at session start, defaulting to `postgresql://$USER@localhost:5432/vibey_test`). After lane `fakes-harness-decouple` lands it is marked `integration`, and runs when `VIBEY_TEST_DATABASE_URL` is set. It is never this lane's only proof.

## Out of scope
- The process launcher, the injected spawner and resolver seams, and moving `isolate_python_env` (child lane 2, `split-367-2-process-launcher`).
- Any loop-service, router, seat-host or queue code (ADR-0046's lanes).
- Converting the existing adapter tests away from patching (lanes `fakes-engines` and `fakes-process-spawner` own that).
- `src/vibey/infrastructure/engines/tailer.py`.
- Changing any behaviour.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject.

## Standing constraints
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
- **Line 1 of every new file** is the provenance comment, copied byte for byte from a sibling file.
- **Substitution at a declared seam only:** constructor or keyword injection, or an injected callable. Never `monkeypatch.setattr` on a module or class attribute, `mock.patch`, `MagicMock` or `AsyncMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` are allowed.
- **Editing:** change existing files with `edit_file` (an exact, unique `old_string` copied from `read_file`), never `write_file`, for any existing file over 100 lines. Never rewrite an existing test file. After each change, run the focused tests.
- **Arch Linux and macOS (8.h):** nothing here is OS-specific; the tests use `tmp_path` and pure Python only.

**Depends on:** none
- none: it edits only code that is on the integration branch today.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
