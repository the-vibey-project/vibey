## Title
feat(qwenloop): a checked guard restores tracked files that one storm attempt gutted, with its thresholds as configuration keys

## Why
The QwenStorm restores, after every attempt, any tracked file that a whole-file rewrite
gutted: 40 lines or more at `HEAD`, and more than half of them lost
(`STORM/qwenlane.py:37-60`, `restore_destroyed_files`; used at `:121-130`). The rule lives in a
script beside a scratch checkout, runs `git` inline, and its two thresholds are literals. The
in-tree storm (`qwenloop run --storm`, `src/vibey_runners/qwen/src/qwenloop/cli/app.py:373-474`)
has no such guard at all.

This lane brings the rule into the runner as a declared, tested class (9.b,
`src/vibey_tools/gh/docs/doctrines.md:349`) whose thresholds are configuration keys with their
defaults stated (12.c, `doctrines.md:455`). A lane's claim of completion is never evidence by
itself (9.c, `doctrines.md:351`); an attempt whose change was a gutted file did not converge.
Wiring it into `_run_storm` is the next lane (`gap-storm-3-gutted-file-wiring`). This is a
child of `gap-spike-storm-command` that is exact without the spike's decisions.

## Required behaviour
1. `QwenConfig` (`src/vibey_runners/qwen/src/qwenloop/domain/config.py:20-34`) gains two
   fields after `endpoint_timeout_seconds`, each with a comment:
   - `storm_gutted_min_lines: int = 40` -- a tracked file shorter than this at `HEAD` is never
     judged gutted;
   - `storm_gutted_loss_fraction: float = 0.5` -- a file is gutted when its net lost lines
     exceed this fraction of its `HEAD` length.
   `QwenConfigParser.parse` (`:59-93`) reads them with the same `data.get(key, default)` pattern
   (`int(...)` and `float(...)`), and refuses `storm_gutted_min_lines < 1` with
   `ValueError("storm_gutted_min_lines must be at least 1")` and a fraction outside `(0, 1)`
   with `ValueError("storm_gutted_loss_fraction must be between 0 and 1")`. They are
   config-file keys, like every other key without an entry in
   `SettingsLoader.ENVIRONMENT_KEYS` (`infrastructure/settings.py:33`).
2. New `src/vibey_runners/qwen/src/qwenloop/infrastructure/gutted_files.py` (provenance line 1,
   copied from `infrastructure/settings.py:1`) holds:
   - `class SubprocessGitWorktree` implementing `GitWorktreeInterface`, every call an argv list
     with `cwd=worktree`, `capture_output=True`, `text=True` (`# nosec B603 B607`, with the
     reason "fixed argv, git on PATH"):
     - `changed_line_counts(self, worktree: Path) -> tuple[tuple[str, int, int], ...]` --
       `git diff --numstat` with `check=True`; each row `added<TAB>deleted<TAB>path` becomes
       `(path, added, deleted)`; binary rows (`-`) are skipped.
     - `head_line_count(self, worktree: Path, path: str) -> int` -- `git show HEAD:<path>`
       with `check=False`; the number of `"\n"` in its stdout, or `0` when git fails (a new file).
     - `restore(self, worktree: Path, path: str) -> None` -- `git checkout -- <path>`, `check=True`.
   - `class GuttedFileGuard` implementing `GuttedFileGuardInterface`:
     - `__init__(self, *, git: GitWorktreeInterface | None = None, min_lines: int = 40, loss_fraction: float = 0.5) -> None`
       (`None` means `SubprocessGitWorktree()`); the same two refusals as the parser.
     - `@classmethod from_config(cls, config: QwenConfig, *, git: GitWorktreeInterface | None = None) -> "GuttedFileGuard"`.
     - `restore_gutted(self, worktree: Path) -> tuple[str, ...]`: for each changed file,
       `before = head_line_count(...)`; when `before >= min_lines` and
       `deleted - added > int(before * loss_fraction)`, it restores the file and adds the path.
       It returns the restored paths in `--numstat` order. With the defaults this is exactly
       `qwenlane.py:56` (`before >= 40 and int(deleted) - int(added) > before // 2`).
3. New `src/vibey_runners/qwen/src/qwenloop/infrastructure/interfaces/gutted_files_interface.py`
   (provenance line 1) declares `GitWorktreeInterface` and `GuttedFileGuardInterface`
   (`restore_gutted`), docstrings only. Export both from
   `infrastructure/interfaces/__init__.py` if that module re-exports its siblings.
4. `tests/fakes.py` gains `ScriptedGitWorktree(rows, head_lines)`: `changed_line_counts`
   returns `rows`; `head_line_count` returns `head_lines.get(path, 0)`; `restore` appends to
   `restored`. Register it for `GitWorktreeInterface` in `tests/test_port_parity.py`, and list
   `GuttedFileGuardInterface` as a class contract there.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/domain/config.py` (edit_file).
- New `src/qwenloop/infrastructure/gutted_files.py` and
  `src/qwenloop/infrastructure/interfaces/gutted_files_interface.py` (under `src/vibey_runners/qwen/`).
- `src/vibey_runners/qwen/tests/fakes.py`, `tests/test_port_parity.py` (append / edit_file).
- New `src/vibey_runners/qwen/tests/test_gutted_files.py`.
- If `src/vibey_runners/qwen` does not exist because `loops-rename` has already renamed the
  tenant, stop and report it.

## Acceptance criteria
- [ ] With the defaults, the guard restores exactly what `qwenlane.py:37-60` restores (the
      boundary tests below).
- [ ] An unknown config key is still refused; the two new keys are accepted and validated.
- [ ] The tenant's floor holds (100% branch coverage of `qwenloop`); mypy, lint-imports and
      bandit pass.

## Tests to write first (TDD)
`src/vibey_runners/qwen/tests/test_gutted_files.py`:
- `test_a_long_file_that_lost_most_of_its_lines_is_restored` -- `("a.py", 3, 30)` with 40 lines at HEAD: restored.
- `test_the_boundaries_match_the_storm_rule` -- 39 lines at HEAD never restored; with 40 lines, a net loss of 20 is kept and 21 is restored.
- `test_a_new_file_and_a_binary_row_are_left_alone` -- a path absent at HEAD (0 lines) and a numstat `-` row.
- `test_thresholds_come_from_config` -- `GuttedFileGuard.from_config(QwenConfig(storm_gutted_min_lines=10, storm_gutted_loss_fraction=0.25), git=...)` restores `("b.py", 0, 3)` with 10 lines at HEAD.
- `test_bad_thresholds_are_refused` -- by the parser and by the constructor, with the stated messages.
- `test_against_a_real_repository` -- `git init` in `tmp_path`, commit a 50-line file, overwrite it with 5 lines, `SubprocessGitWorktree` + guard restores it and the file has 50 lines again (local git only; no network).
- `test_guard_and_worktree_satisfy_their_interfaces`.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && pip install -e ".[dev]"
    cd src/vibey_runners/qwen && mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    cd src/vibey_runners/qwen && python -m pytest -q
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Calling the guard from `_run_storm` (`gap-storm-3-gutted-file-wiring`); `STORM/*` scripts;
  environment overrides for the two keys.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(qwenloop): a checked guard restores files a storm attempt gutted`. Do not push.

## Lane card
- **Depends on:** `fakes-tenant-qwen-1` (the tenant's `tests/fakes.py` and parity registry).
- **Standing constraints:** the tenant's own gates on its floor (ADR-0022); tenants never
  import `vibey`; a fake is a plain class; substitution only at declared seams.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
