## Title
feat(gh): `vibey-gh runners render|check` reconciles the sovereign runner's units from the tree

## Why
`gap-runners-declared-1` declared `[runners]`, and `-2` renders units from it. The operator
still needs one command to write the units and one to prove the installed ones match the tree
(12.c, `src/vibey_tools/gh/docs/doctrines.md:455`: "reconciled, not merely written"). A
meta-test also keeps the in-tree supervisor, imported by `gap-ops-runner-assets-import`,
wired to the variables the units set.

## Required behaviour
1. In `src/vibey_tools/gh/vibey_gh/cli.py`, add a subparser `runners` next to `sovereign`
   (`:1603-1609`). It has two sub-actions:
   - `vibey-gh runners render --target {launchd,systemd} [--out DIR]`. Default `DIR`:
     `~/Library/LaunchAgents` for launchd, `~/.config/systemd/user` for systemd.
     - It writes each `RenderedUnit`, creating `DIR` when missing, and prints
       `wrote <path>` per unit.
     - It exits 1 and prints the problem when `render` returns one.
     - It never loads or starts a unit. It prints the exact next command for the operator:
       launchd `launchctl bootstrap gui/$(id -u) <path>`; systemd `systemctl --user daemon-reload && systemctl --user enable --now <name>`.
   - `vibey-gh runners check --target {launchd,systemd} [--dir DIR]`. It prints each problem
     from `RunnerUnits.check` and exits 1 when any exists, `0` with
     `vibey-gh runners: <target> units match the tree` otherwise.
   - A private function `_runners(args) -> int` builds
     `RunnerUnits(home=Path(os.environ.get("HOME", "~")).expanduser())` and reads
     `load_config()` (`runners`, `pr_automation.fallback`, `platform`). Follow `_sovereign`'s
     style (`:678-706`).
2. A meta-test in `src/vibey_tools/gh/test/test_runners.py`, appended:
   `test_the_in_tree_supervisor_reads_the_variables_the_units_set`. It runs only when the root's
   `deploy/runners/vibey-runner.sh` exists (skip with a reason otherwise; its source is
   `gap-ops-runner-assets-import`). It asserts the file references each of `VIBEY_REPO_URL`,
   `VIBEY_RUNNER_LABEL`, `VIBEY_RUNNER_IMAGE`, `VIBEY_OLLAMA_URL` and `VIBEY_REQUIRE_AC`, and
   that `vibey-local-authority.sh` references `VIBEY_RUNNER_UNIT_PREFIX`.
3. CLI tests use `main([...])` with `--out`/`--dir` pointing at `tmp_path`, and a `HOME` given
   through `monkeypatch.setenv`. The environment is a declared seam; there is no patching of imports.

## Where to change
- `src/vibey_tools/gh/vibey_gh/cli.py` (large; edit_file only).
- Append to `src/vibey_tools/gh/test/test_runners.py`, plus CLI tests in the same file.

## Acceptance criteria
- [ ] `vibey-gh runners render --target launchd --out <tmp>` writes the two plists and prints the `launchctl bootstrap` hint.
- [ ] `vibey-gh runners check --target launchd --dir <tmp>` exits 0 right after, and exits 1
      naming `drift:` after one byte of a plist changes.
- [ ] An unknown target is refused by argparse (exit 2), and an underivable URL exits 1 with the problem text.
- [ ] The meta-test passes once `deploy/runners/` exists, and skips with its reason before then.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_runners.py`:
- `test_cli_render_writes_units_and_prints_the_next_command`
- `test_cli_check_detects_drift`
- `test_cli_render_reports_an_underivable_url`
- `test_the_in_tree_supervisor_reads_the_variables_the_units_set`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Loading or starting units (the operator does that).
- Changing the supervisor script's behaviour, and docs.

Commit as `feat(gh): vibey-gh runners render and check`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
