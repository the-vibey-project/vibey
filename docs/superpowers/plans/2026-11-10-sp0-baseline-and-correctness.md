# SP0 Baseline and Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the correctness bugs the scans found that can be fixed inside this worktree, and
commit the CI baseline, before any optimization work moves code under them.

**Architecture:** Five independent tasks, each ending in a test that failed first. No task
changes a required check, a GitHub setting or a published artifact outside this repository.

**Tech Stack:** Python 3.12, pytest (with xdist), ruff, mypy `--strict`, hatchling, GitHub Actions YAML.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md` (SP0), PR #1867.

## Global Constraints

- Work only in this worktree. Do not push, merge, publish, or change any GitHub or TestPyPI setting.
- Domain stays pure (`src/vibey/domain/`: no I/O, async, clock or network).
- New and changed classes get an interface beside them: `src/<pkg>/x/y.py` implies
  `src/<pkg>/x/interfaces/y_interface.py`. Interfaces declare; they never consume.
- 100% branch coverage on `src/vibey/{domain,application,infrastructure,cli}`; each task's new
  code is fully covered by its own tests.
- `mypy --strict src/vibey`, `ruff check .`, `ruff format --check .` stay clean.
- Configuration is declared in config or TOML, never a literal in source (12.c).
- Commits are Conventional Commits and end with the trailer
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Run `git commit` in the foreground.
- Never edit a file while a git hook is running in this worktree.
- Migrations are never edited. No task here adds one.

## Review Focus

1. A writer that flushes half a JSON line and then the rest produces the event exactly once;
   a complete but invalid line is still skipped with the existing warning, and never retried.
2. A final line with no trailing newline is still delivered once the run has reached a terminal
   status, and not before.
3. A telemetry cap never drops the most recent span or the most recent sample.
4. The sdist budget test fails loudly when someone adds a large tree, and names it.

---

### Task 1: Tail events.jsonl by byte offset

**Files:**
- Create: `src/vibey/infrastructure/engines/events_tail.py`
- Create: `src/vibey/infrastructure/engines/interfaces/events_tail_interface.py`
- Modify: `src/vibey/infrastructure/engines/loop_process_adapter.py` (the `tail` method, the
  `seen_lines` loop that starts at the comment "Tail the file")
- Test: `tests/infrastructure/engines/test_events_tail.py` (new),
  `tests/infrastructure/engines/test_loop_process_adapter.py` (extend)

**Interfaces:**
- Produces:
  - `EventsTailInterface` (Protocol) with `read_new(self) -> list[str]` and
    `flush(self) -> list[str]`.
  - `EventsTail(path: Path)` implementing it.
    - `read_new()` returns the complete lines (without the trailing newline) written since the
      last call and keeps the byte offset after the last newline.
    - `read_new()` holds back a final line that has no newline yet.
    - `flush()` returns that held-back remainder, if any, and clears it.
    - A missing file reads as no lines.
    - It reads bytes and decodes each line as UTF-8 with `errors="replace"`.
- Consumes: `LoopProcessAdapter.tail` in the same module, which already yields `EngineEvent`.

- [ ] **Step 1: Write the failing tests** in `test_events_tail.py`, with the names and
  assertions below (use `tmp_path`):
  - `test_returns_only_new_complete_lines`: write `"a\nb\n"`, `read_new() == ["a", "b"]`; append
    `"c\n"`, `read_new() == ["c"]`; a further call returns `[]`.
  - `test_holds_back_a_half_written_line`: write `'{"x":'` with no newline, `read_new() == []`;
    append `'1}\n'`, `read_new() == ['{"x":1}']`.
  - `test_flush_returns_a_final_unterminated_line_once`: write `"a\nb"`; `read_new() == ["a"]`;
    `flush() == ["b"]`; `flush() == []`.
  - `test_missing_file_reads_as_empty`: `read_new() == []` and `flush() == []`.
  - `test_multibyte_character_split_across_reads_is_not_corrupted`: write the first byte of
    `"é"` (b"\xc3") without a newline, then append `b"\xa9\n"`; `read_new() == ["é"]`.
  - `test_blank_lines_are_returned_as_empty_strings`: write `"a\n\nb\n"`; `read_new() == ["a", "", "b"]`.
  In `test_loop_process_adapter.py`, add `test_tail_delivers_a_line_flushed_in_two_pieces`:
  follow the existing `test_tail_yields_translated_events` fixture; write the first half of one
  valid event line, start `adapter.tail(handle)`, append the second half plus newline and the
  terminal `meta.json` status, and assert exactly one `EngineEvent` for it.
  Add `test_tail_delivers_a_final_line_with_no_newline_after_terminal_status` asserting the
  event is yielded once the terminal status is written (Review Focus 2).
  Add `test_tail_still_skips_a_complete_invalid_line_once` asserting one warning and no retry.
- [ ] **Step 2: Run them and confirm they fail** (module not found, then assertion failures):
  `uv run pytest tests/infrastructure/engines/test_events_tail.py tests/infrastructure/engines/test_loop_process_adapter.py -q -p no:cacheprovider`
- [ ] **Step 3: Implement `EventsTail` and its interface.** Keep `self._offset: int` and
  `self._pending: bytes`. Open the file in binary mode per call, seek to `self._offset`, read to
  end, split on `b"\n"`; the last element is the new pending remainder.
- [ ] **Step 4: Replace the line-list loop in `LoopProcessAdapter.tail`.** Construct one
  `EventsTail(events_path)` before the loop; each iteration gets
  `lines = await asyncio.to_thread(tail.read_new)` instead of `read_text().splitlines()`; delete
  `seen_lines` and `lines[seen_lines:]`; skip empty lines as today. Immediately before each of the
  two `break`/give-up exits (terminal `meta.json` status, and the process-exited path), process
  `tail.flush()` through the same per-line translation. Extract the per-line translation into a
  private method so both paths share it; do not change its translation rules or log events.
- [ ] **Step 5: Run the tests and the module's coverage** and confirm all pass and the new and
  changed lines are fully covered:
  `uv run pytest tests/infrastructure/engines -q -p no:cacheprovider --cov=vibey.infrastructure.engines --cov-branch --cov-report=term-missing`
- [ ] **Step 6: Run ruff and `mypy --strict`** on the touched files and commit:
  `git add src/vibey/infrastructure/engines tests/infrastructure/engines && git commit -m "fix(engines): tail events.jsonl by byte offset so a half-written line is not lost"`

---

### Task 2: Bound the in-process telemetry buffers

**Files:**
- Modify: `src/vibey/infrastructure/otel.py` (`TelemetryTracer`, `TelemetryMetrics`)
- Modify: `src/vibey/domain/config.py:240` (`TelemetryConfig`) and `src/vibey/bootstrap.py:1017-1018`
- Test: `tests/infrastructure/test_otel.py` (extend), the config loader test that covers
  `TelemetryConfig` (find it with `grep -rn TelemetryConfig tests`)

**Interfaces:**
- Produces:
  - `TelemetryConfig` gains `max_spans: int = 10_000` and `max_samples: int = 1_000`; both must
    be `>= 1` (a `ConfigError` otherwise, as the neighbouring config classes do).
  - `TelemetryTracer(max_spans: int = 10_000)` keeps only the newest `max_spans` finished spans
    (`collections.deque(maxlen=max_spans)`); `get_finished_spans()` and `clear()` keep their
    signatures.
  - `TelemetryMetrics(max_samples: int = 1_000)` keeps only the newest `max_samples` values in
    each latency or duration list. Counters (`_selections`, `_handoff_failures`,
    `_cost_spend`) are bounded by distinct keys and stay as they are.
    `export_metrics` keeps its return shape; its lists are plain `list[float]`.
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Write the failing tests** in `tests/infrastructure/test_otel.py`:
  - `test_tracer_keeps_only_the_newest_spans`: `TelemetryTracer(max_spans=3)`, record spans named
    `s0` to `s9`, assert `[s.name for s in get_finished_spans()] == ["s7", "s8", "s9"]`
    (Review Focus 3).
  - `test_tracer_default_cap_is_ten_thousand`: record 10_005 spans, assert length `10_000` and the
    last span is the newest.
  - `test_metrics_keep_only_the_newest_samples`: `TelemetryMetrics(max_samples=2)`, record queue
    latencies `1.0, 2.0, 3.0` for one project and job kind, assert the exported list is `[2.0, 3.0]`;
    the same for phase durations.
  - `test_metrics_counters_are_unaffected_by_the_cap`: the three counters still sum every call.
  - Config tests: defaults are 10_000 and 1_000; `max_spans = 0` and `max_samples = 0` raise `ConfigError`;
    values load from a `[telemetry]` table in `vibey.toml`.
  - A bootstrap-wiring test that the tracer and metrics built by `bootstrap.py` receive the
    configured caps (follow how existing bootstrap tests read `telemetry_tracer`).
- [ ] **Step 2: Run them and confirm they fail.**
  `uv run pytest tests/infrastructure/test_otel.py tests/domain -q -p no:cacheprovider -k "telemetry or otel"`
- [ ] **Step 3: Implement the caps** in `otel.py`: replace `self._spans: list[Span]` with a bounded
  deque; keep latency and duration lists as `deque(maxlen=max_samples)` internally and convert to
  `list` in `export_metrics`. Add the two config fields and their validation; pass the config
  values in `bootstrap.py` where `TelemetryTracer()` and `TelemetryMetrics()` are constructed
  (read the resolved config the way the surrounding code does; the construction currently happens
  before the config is resolved, so move it after, without changing what else runs first).
- [ ] **Step 4: Run the telemetry, config and bootstrap tests** and the 100% coverage floor for
  `src/vibey/infrastructure` and `src/vibey/domain`:
  `uv run pytest tests -q -p no:cacheprovider -k "otel or telemetry or config or bootstrap"`
  then `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=` followed by
  `uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100` and the same
  for `domain`.
- [ ] **Step 5: Document the new keys** in `docs/reference/configuration.md` where
  `[telemetry]` is described, then ruff, mypy and commit:
  `git commit -m "fix(telemetry): bound the in-process span and sample buffers"`

---

### Task 3: Keep the sdist small, with a budget test

**Files:**
- Modify: `pyproject.toml` (add `[tool.hatch.build.targets.sdist]`)
- Create: `tests/meta/test_sdist_contents.py`, `tests/meta/sdist_budget.toml`

**Interfaces:**
- Produces: an sdist whose file list excludes everything in the table below, and a meta test
  that fails when it ships one of them again or exceeds the declared size budget.

Today the sdist is 31 MB and ships `docs/microslices` (5,558 files), `docs/explorer` (1,435),
`.hypothesis/constants` (1,151), `docs/plans`, `research`, `clients`, `tests`. Each develop push
uploads wheel plus sdist (about 38 MB) to TestPyPI, which has now refused uploads at its 10 GB
project limit.

- [ ] **Step 1: Write the failing meta test.** In `tests/meta/test_sdist_contents.py`, list the
  files hatchling would put in the sdist without building it:
  `from hatchling.builders.sdist import SdistBuilder`, `SdistBuilder(str(ROOT)).recurse_included_files()`
  (each item has `.relative_path` and `.path`). Read the budget and the forbidden prefixes from
  `tests/meta/sdist_budget.toml`:
  `max_total_mib = 12`, `forbidden_prefixes = ["docs/microslices", "docs/explorer", "docs/plans", ".hypothesis", ".mypy_cache", "research", "clients", "tests", "deploy/helm/vibey/ci"]` (add every
  other top-level tree you find over 1 MiB that the source distribution does not need to build
  the wheel, with a one-line reason as a TOML comment beside it).
  Tests: `test_sdist_ships_no_forbidden_tree` (names every offender and its file count),
  `test_sdist_is_within_budget` (sum of file sizes in MiB, names the five largest top-level
  trees when it fails), `test_sdist_still_ships_what_the_wheel_needs` (every path under
  `[tool.hatch.build.targets.wheel] packages` and `force-include` sources is in the sdist),
  and `test_the_budget_has_no_unused_prefix` (each forbidden prefix exists in the repository, so
  the list shrinks when its reason goes).
- [ ] **Step 2: Run it and confirm it fails** for the forbidden trees and the budget.
  `uv run pytest tests/meta/test_sdist_contents.py -q -p no:cacheprovider`
- [ ] **Step 3: Add the sdist table** to `pyproject.toml` with `include` of exactly what a
  source build needs (`/src`, `/pyproject.toml`, `/README.md`, `/LICENSE*`, `/CHANGELOG.md` if the
  wheel metadata reads it) or `exclude` of the forbidden prefixes, whichever keeps the wheel's
  force-included sources present; confirm the third test passes. Do not change the wheel's own file list.
- [ ] **Step 4: Verify the real artifact:** build `uv build --sdist --out-dir "$TMPDIR/sdist"` and
  `uv build --wheel --out-dir "$TMPDIR/wheel"`; record both sizes in the task report. Confirm the
  wheel is unchanged in file count from `origin/develop`'s build (`unzip -l | wc -l`, built in a
  clean checkout of `origin/develop` via `git stash`-free means: use `git worktree add` under
  `$HOME/git/vibey-storm/`), and install the new sdist's wheel build in a venv and run
  `vibey --version`.
- [ ] **Step 5: Commit:**
  `git commit -m "fix(release): keep the sdist to what a source build needs"`

---

### Task 4: Make a failed develop publish loud

**Files:**
- Modify: `.github/workflows/vibey-engine.yml` (job `testpypi`, after the publish step)
- Test: `tests/meta/test_release_failure_is_loud.py` (new)

**Interfaces:**
- Produces: when `testpypi` fails, a step opens an issue (or comments on the open one) titled
  `Release: develop publish failed`, labelled `release-health`, containing the run URL and the
  failing step. It never runs on success.

- [ ] **Step 1: Write the failing meta test.** Parse the workflow YAML (`yaml.safe_load`; `pyyaml`
  is already a test dependency). Assert: the `testpypi` job has a step with
  `if: failure()` whose `run` contains `gh issue`; that step's job `permissions` include
  `issues: write`; the step body searches for an existing open issue with that exact title before
  creating one (`gh issue list --state open --search`), so repeated failures add a comment
  instead of an issue per push; the publish step itself keeps `continue-on-error` unset (the job
  must still fail).
- [ ] **Step 2: Run it and confirm it fails.**
  `uv run pytest tests/meta/test_release_failure_is_loud.py -q -p no:cacheprovider`
- [ ] **Step 3: Add the step** and the `issues: write` permission. Use `GH_TOKEN: ${{ github.token }}`
  and `gh issue create --label release-health` falling back to creating the label if absent
  (`gh label create release-health --color B60205 --description "A release job failed" || true`).
  Include in the issue body one line pointing at the TestPyPI storage-limit cause so an operator
  who sees it knows where to look first.
- [ ] **Step 4: Confirm the workflow YAML still parses and nothing else in it changed:**
  `git diff --stat .github/workflows/vibey-engine.yml` shows only this job, and
  `uv run pytest tests/meta -q -p no:cacheprovider -k "workflow or release"` passes.
- [ ] **Step 5: Commit:**
  `git commit -m "fix(release): open an issue when the develop publish fails"`

---

### Task 5: Record the workflow state and commit the CI baseline

**Files:**
- Create: `docs/architecture/evidence/ci-workflow-state-2026-11-10.md`
- Create: `docs/architecture/evidence/ci-cost-baseline-2026-11-10.json`
- Create: `scripts/ci_cost_baseline.py` and `scripts/ci_cost_baseline.toml`,
  `scripts/interfaces/ci_cost_baseline_interface.py`
- Test: `tests/scripts/test_ci_cost_baseline.py`

**Interfaces:**
- Produces: `CiCostBaseline` (in `scripts/ci_cost_baseline.py`) implementing
  `CiCostBaselineInterface` with `collect(self, since_days: int) -> dict[str, object]`, built from
  read-only `gh api` calls through the existing `CommandRunnerInterface` pattern in
  `scripts/minimum_specs.py` (reuse `SubprocessRunner`; do not add a new HTTP client). The record
  holds, per workflow: trigger events seen, run count, conclusion counts, wall time p50 and p90 in
  minutes, and job-minutes split by runner OS. It records the window and the cutoff, per
  sub-doctrine 10.f, and states that billed dollars are 0 for a public repository.
  This task builds the baseline as a script; promoting it to a `vibey-gh` command is SP1's CI-L.

- [ ] **Step 1: Write the failing tests** in `tests/scripts/test_ci_cost_baseline.py` with a fake
  runner answering fixture JSON shaped like `gh api repos/.../actions/runs` and `.../runs/<id>/jobs`:
  percentile maths (p50/p90 on an even and an odd count), OS split (ubuntu, macos, windows labels),
  a run with no jobs, a window cutoff that excludes older runs, pagination stops at the cutoff,
  and `collect` records which workflows are `disabled_manually` from the workflows listing.
- [ ] **Step 2: Run them and confirm they fail.**
  `uv run pytest tests/scripts/test_ci_cost_baseline.py -q -p no:cacheprovider`
- [ ] **Step 3: Implement the class, the TOML (repo slug, window days, sample size per workflow,
  output path) and the interface.** Settings come from the TOML only; nothing hard-coded.
- [ ] **Step 4: Run it against the live repository** (read-only): `uv run python scripts/ci_cost_baseline.py collect`
  and commit its JSON output to `docs/architecture/evidence/ci-cost-baseline-2026-11-10.json`.
  Sandbox network and gh cache may need the sandbox disabled for this one command; say so in the report.
- [ ] **Step 5: Write `ci-workflow-state-2026-11-10.md`** from the collected data: one row per
  workflow with its state (active or `disabled_manually`), triggers, last run date and conclusion,
  and a column "why disabled" that says `unknown, operator to say` where the repository holds no
  record (search `docs/`, `CHANGELOG.md`, `.vibey-gh.toml` comments and `git log` for each name before
  concluding that). No guessing.
- [ ] **Step 6: Commit:**
  `git commit -m "docs(ci): record the workflow state and a cost baseline before optimizing it"`

---

## Not in this plan (needs the operator, or is its own sub-plan)

- Enforcing the merge queue and removing the admin bypass: a repository-settings change through
  `.vibey-gh.toml` and reconcile. Stop-class; the operator decides when to apply it.
- Purging old TestPyPI dev releases or requesting a size-limit increase: an external account action.
- Replacing the in-process telemetry with the real OpenTelemetry API (Decision 4): its own
  sub-plan, after Task 2 lands the bound.
- The hollow `pragma: no cover` floors and the bootstrap branch floor: SP4.
