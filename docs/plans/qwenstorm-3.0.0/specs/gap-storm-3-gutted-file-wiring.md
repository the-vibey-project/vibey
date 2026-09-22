## Title
feat(qwenloop): the storm restores gutted files after every attempt, tells the next attempt, and never counts a gutted attempt as converged

## Why
Lane `gap-storm-2-gutted-file-guard` gave the runner a checked `GuttedFileGuard`. The in-tree
storm still does not call it: `_run_storm` runs each attempt and accepts a `COMPLETED` status
as convergence (`src/vibey_runners/qwen/src/qwenloop/cli/app.py:443-452`). The QwenStorm
driver does three things after every attempt that the runner does not
(`STORM/qwenlane.py:121-149`): it restores gutted files, it tells the next attempt which files
were restored and how to re-apply its change, and it refuses to count a completion whose only
change was restored. A verdict or a completion marker is never convergence evidence by itself
(9.c, `src/vibey_tools/gh/docs/doctrines.md:351`; 10.f, `:419`).

The guard is reached through the CLI's declared composition (`QwenloopComposition`, lane
`fakes-tenant-qwen-2`), never by patching (9.b, `doctrines.md:349`).

## Required behaviour
1. `QwenloopComposition` (`src/vibey_runners/qwen/src/qwenloop/cli/composition.py`, lane
   `fakes-tenant-qwen-2`) gains the keyword field
   `gutted_guard: Callable[[QwenConfig], GuttedFileGuardInterface]`, default
   `GuttedFileGuard.from_config`, and its interface gains the same attribute.
2. `app.py` gains, beside `_run_storm`, the constant
   `RESTORED_FILES_NOTICE = ("\n## Files restored after the previous attempt\n" "These files lost most of their lines to a whole-file rewrite and were restored " "from git: {paths}. Re-apply only your intended change to each, using the targeted " "replacement in the Lane editing rules.\n")`
   (the text of `qwenlane.py:124-129`).
3. In `_run_storm`, build `guard = QwenloopComposition.current().gutted_guard(config)` once,
   next to `server, profile = _server_for(config)` (`app.py:385`). After each attempt's
   `repo_turns += state.turns` / `item_turns += state.turns` (`:443-444`), and before the
   `COMPLETED` check:
   ```python
                try:
                    restored = guard.restore_gutted(repo_dir)
                except (OSError, subprocess.CalledProcessError) as exc:
                    restored = ()
                    typer.echo(f"{name} {label}\tguard-unavailable\t{exc}")
                if restored:
                    typer.echo(f"{name} {label}\trestored\t{', '.join(restored)}")
                    plan_text += RESTORED_FILES_NOTICE.format(paths=", ".join(restored))
   ```
   (`plan_text` is the loop variable from `for label, plan_text in plans:`; later attempts of
   the same item start from it.) A guard that cannot run is said, never silent (7.c).
4. The `COMPLETED` branch (`:445-452`) runs only when nothing was restored:
   `if state.status is RunStatus.COMPLETED and not restored:`. When the status is `COMPLETED`
   but files were restored, it echoes
   `f"{name} {label}\tattempt {attempt}/{max_attempts}\tclaimed-complete-with-restored-files\t{state.turns}"`
   and moves to the next attempt, exactly as a failed attempt does. Every other line and the
   final tally keep their text.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/cli/composition.py` and its interface (edit_file).
- `src/vibey_runners/qwen/src/qwenloop/cli/app.py` (edit_file only; 761 lines).
- `src/vibey_runners/qwen/tests/test_cli.py`: append the tests below; never rewrite it. Build
  the composition with `gutted_guard=lambda config: GuttedFileGuard(git=ScriptedGitWorktree(...))`
  and the scripted runner and GitHub reader from `tests/fakes.py`, following the storm tests at
  `tests/test_cli.py:349-392` and `:461-509` as `fakes-tenant-qwen-2` left them.

## Acceptance criteria
- [ ] Every existing storm test in `tests/test_cli.py` passes unchanged (their repositories are
      not real git repositories, so they see `guard-unavailable` lines and nothing else changes).
- [ ] A completed attempt whose change was restored is not counted as completed.
- [ ] The tenant's floor holds; mypy, lint-imports and bandit pass; the ratchet is not raised.

## Tests to write first (TDD)
Append to `src/vibey_runners/qwen/tests/test_cli.py`:
- `test_storm_restores_gutted_files_and_tells_the_next_attempt` -- attempt 1 returns `completed` with `a.py` gutted (scripted `("a.py", 1, 45)`, 50 lines at HEAD); the output has `restored\ta.py`, attempt 1 is `claimed-complete-with-restored-files`, and the plan the scripted runner received on attempt 2 contains `## Files restored after the previous attempt` and `a.py`.
- `test_storm_counts_a_completion_only_when_nothing_was_restored` -- attempt 2 completes with no rows: the item is `completed ... (attempt 2/3)` and the tally is `(1/1 items completed)`.
- `test_storm_says_when_the_guard_cannot_run` -- a guard whose `restore_gutted` raises `OSError("no git")` gives `guard-unavailable\tno git` and the storm carries on.
- `test_composition_defaults_the_guard_to_production` -- `QwenloopComposition().gutted_guard(QwenConfig())` is a `GuttedFileGuard`.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && pip install -e ".[dev]"
    cd src/vibey_runners/qwen && mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    cd src/vibey_runners/qwen && python -m pytest -q
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The no-surviving-change half of `qwenlane.py:131-149` (it needs the storm's declared
  exclusions; the spike's ADR owes it); `STORM/*` scripts; single-plan `qwenloop run`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(qwenloop): the storm restores gutted files and never counts a gutted attempt as converged`. Do not push.

## Lane card
- **Depends on:** `gap-storm-2-gutted-file-guard`, `fakes-tenant-qwen-2` (the composition and the
  converted `test_cli.py`), `gap-storm-1-editing-rules` (the notice points at those rules).
- **Standing constraints:** the tenant's own gates on its floor; tenants never import `vibey`;
  substitution only through `ctx.obj`; if `src/vibey_runners/qwen` has been renamed by
  `loops-rename`, stop and report.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
