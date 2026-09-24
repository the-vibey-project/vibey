## Title
feat(vscodeloop): the run directory — events, meta, inbox and stop summary

ADR-0046 lane L20e (slug `loops-vscodeloop-run-store`).

## Why
vibey reads every runner through one file contract, whichever loop runs it: it tails
`events.jsonl`, stops when `meta.json`'s `status` is terminal, writes commands into the run's
`inbox/`, and waits up to 30 s for `stop-summary.md` after a stop
(`src/vibey/infrastructure/engines/loop_process_adapter.py:418-589`, `:591-614`, `:651-673`
at integration `d3b4a388`; lane `split-367-1-run-dir` moves these into
`infrastructure/engines/run_dir.py`). ADR-0046 §8 (`specs/ADR-two-loops.md:268`) fixes
vscodeloop's layout: `.vscodeloop/runs/<run_id>/` with `events.jsonl`, `meta.json`, a control
inbox and `stop-summary.md`. The dropped `specs/opencodeloop-parity-p1.md` behaviours 11–13
defined the run files, the inbox and the wind-down file; they carry over here.

The closest existing store is `src/vibey_runners/opencode/src/opencodeloop/infrastructure/run_store.py`
(61 lines, above). This lane writes vscodeloop's own, with the parity rules.

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. **`vscodeloop/application/interfaces/store_interface.py`** (new; plus `application/__init__.py`
   and `application/interfaces/__init__.py`): `@runtime_checkable class RunStoreInterface(Protocol)`
   with exactly the methods of behaviour 2.
2. **`vscodeloop/infrastructure/run_store.py`** (new; plus `infrastructure/__init__.py`):
   `SCHEMA_VERSION = 1`, `STATE_DIR = ".vscodeloop"`, and `class FileRunStore` with:
   - `run_dir(self, cwd: Path, run_id: str) -> Path` → `cwd / ".vscodeloop" / "runs" / RunId.parse(run_id).value`
     (`from vibey_runners.common.domain import RunId`; an invalid id raises its `ValueError`).
   - `begin(self, run_dir: Path, *, run_id: str, cwd: Path, session_id: str | None) -> None`:
     creates `run_dir`, `run_dir/"snapshots"`, `run_dir/"inbox"` (parents, exist_ok); writes
     `meta.json` `{"run_id", "schema_version", "cwd", "session_id", "status": "active", "updated_at"}`;
     records the names already in `inbox/` so they never count as new (a replayed job's stale
     `stop` must be ignored, parity-p1 behaviour 12).
   - `append_event(self, run_dir: Path, event: Mapping[str, object]) -> None`: appends one line
     `json.dumps({"timestamp": <utc iso>, **event}, sort_keys=True)`; never rewrites earlier lines.
   - `finish(self, run_dir: Path, result: RunResult) -> None`: merges into `meta.json`
     `{"status": result.status.value, "exit_code": result.exit_code, "session_id", "detail",
     "stop_reason": result.stop_reason.value or None, "done_marker": DONE_MARKER if FINISHED else None, "updated_at"}`;
     writes the same object to `snapshots/latest.json`; writes `stop-summary.md` for **every**
     terminal state:
     ```
     # vscodeloop run <run_id>
     status: <status>
     stop_reason: <value or none>
     detail: <detail>
     <DONE_MARKER>            (this line only when the status is finished)
     ```
     Every JSON write is atomic: write `<name>.tmp` then `os.replace`.
   - `new_commands(self, run_dir: Path) -> tuple[InboxCommand, ...]`: every `inbox/*.json` file
     not present at `begin()` and not returned before, sorted by name, parsed; bad JSON is skipped
     (and remembered as seen). Files are never deleted. `InboxCommand(kind: str, text: str | None)`
     is a frozen dataclass in `vscodeloop/domain/model.py` (append it): `kind` is the JSON's
     `command` or `type`, normalized `wind-down` → `wind_down`.
   - `wind_down_requested(self, run_dir: Path) -> bool`: True once any new command has kind
     `stop` or `wind_down` (parity-p1 behaviour 12; vibey's stop writes `{"command": "stop"}`,
     `loop_process_adapter.py:653-657`).
   - `request_wind_down(self, run_dir: Path) -> Path`: writes
     `inbox/<time.time_ns()>-wind_down.cmd.json` = `{"type": "wind_down", "reason": "operator"}`.
   - `write_prompt(self, run_dir: Path, text: str, *, now: bool) -> Path`: writes
     `inbox/<time.time_ns()>-prompt-<now|at-break>.json` = `{"command": "prompt-now"|"prompt-at-break", "text": text}`
     (the same bodies vibey's `RunInbox.write_prompt` writes).
   - `request_stop(self, run_dir: Path) -> Path`: writes `inbox/<time.time_ns()>-stop.json` = `{"command": "stop"}`.
   - `read_meta(self, run_dir: Path) -> Mapping[str, object] | None` (None when missing or unparsable).
3. The clock (`datetime.now(UTC)`, `time.time_ns()`) is injected through the constructor as
   `now: Callable[[], datetime]` and `ns: Callable[[], int]`, defaulting to the real ones, so tests
   pass fixed values (no patching).

## Where to change
- New: `src/vibey_runners/vscode/src/vscodeloop/application/__init__.py`,
  `application/interfaces/__init__.py`, `application/interfaces/store_interface.py`,
  `infrastructure/__init__.py`, `infrastructure/run_store.py`; append `InboxCommand` to
  `domain/model.py` (and its Protocol `InboxCommandInterface` to `domain/interfaces/model_interface.py`).
- New test: `src/vibey_runners/vscode/tests/test_run_store.py` (provenance line 1 copied from `tests/test_domain.py`).

## Acceptance criteria
- [ ] A finished run's `meta.json` has `status == "finished"`, `exit_code == 0` and the marker; a failed one has `done_marker` null and `exit_code == 1`; a wound-down one `status == "stopped"`, `exit_code == 75`.
- [ ] `stop-summary.md` exists after every `finish`, and contains the marker line only when finished.
- [ ] A `stop.json` already in `inbox/` at `begin()` does not count; one written after does.
- [ ] Files written by vibey's `RunInbox` (`{"command": "stop"}`, prompt bodies) parse as commands.
- [ ] An invalid run id (`"../x"`) raises `ValueError` from `run_dir`.
- [ ] The tenant suite passes at 100% branch coverage; mypy strict, lint-imports and bandit pass.

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_run_store.py` (`tmp_path` only):
- `test_begin_writes_an_active_envelope`
- `test_events_are_appended_never_rewritten`
- `test_finish_writes_meta_snapshot_and_summary_for_each_status` (parametrized FINISHED/FAILED/STOPPED)
- `test_writes_are_atomic` (no `*.tmp` left behind; a pre-existing `meta.json.tmp` does not survive)
- `test_commands_present_at_begin_are_stale`
- `test_new_commands_are_returned_once_in_name_order`
- `test_bad_json_in_the_inbox_is_skipped_not_deleted`
- `test_vibey_inbox_bodies_parse` (stop, prompt-now, prompt-at-break, wind-down with a hyphen)
- `test_request_wind_down_and_stop_and_prompt_write_the_family_bodies`
- `test_run_dir_refuses_an_unsafe_run_id`
- `test_store_satisfies_its_interface`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Driving the editor, bounds and the watchdog (`loops-vscodeloop-runner`), the CLI verbs
  (`loops-vscodeloop-cli`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscodeloop-scaffold`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
