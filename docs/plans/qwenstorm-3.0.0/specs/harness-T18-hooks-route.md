## Title
build(hooks): a push runs the suite once, as one harness request with its four coverage gates

## Why
- **Today.** The pre-push stage runs the whole suite twice: `test-suite`
  (`.pre-commit-config.yaml:11-24`) and `coverage-gates` (`:40-45`). The file's own comment says a
  push once ran it three times (`:20-23`), and that `test-suite` survives only so that a plain test
  failure is reported as itself.
- **Under 8.e** (ratified, `src/vibey_tools/gh/docs/doctrines.md:274-277`) those are two
  selections, so two runs, one after the other, on a machine that allows one at a time.
- **Under draft ADR-0045 §8 and §10,** one request carries the four gates, and its answer reports
  test failures and gate failures separately (harness-T15b's report), so `test-suite`'s one reason
  is met and it goes. ADR-0023's four floors are unchanged: the same four globs at 100.
- **Where the change lives.** The hooks chain (ADR-0028): `.githooks/pre-push` →
  `pre-push.local` → `framework-hook.sh` → the pre-commit framework (`.githooks/pre-push:116-118`,
  `.githooks/pre-push.local:5`, `.githooks/framework-hook.sh:55-58`). So the routing belongs in the
  framework config the chain reaches, and **no vibey-gh template changes**: vibey-gh manages
  `commit-msg` and `pre-push` only (`src/vibey_tools/gh/vibey_gh/install.py:34`) and compares them
  with their templates (`:639`).

## Required behaviour
1. **Remove** the `test-suite` hook (`.pre-commit-config.yaml:11-24`), with its comment.
2. **Replace** the `coverage-gates` hook (`:40-45`) with the block below. Keep a comment above it
   saying: why one request (8.e and ADR-0045 §8); that the answer separates test failures from gate
   failures; that `SKIP=coverage-gates git push` is the framework's bypass.
   ```yaml
         - id: coverage-gates
           name: test suite and per-layer 100% coverage gates (one test-harness run)
           entry: >-
             uv run vibey test run
             --gate src/vibey/domain/*=100
             --gate src/vibey/application/*=100
             --gate src/vibey/infrastructure/*=100
             --gate src/vibey/cli/*=100
             -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
           language: system
           pass_filenames: false
           stages: [pre-push]
   ```
   pre-commit splits `entry` with `shlex` and runs no shell, so the `*` is never globbed.
3. **The other hooks** (`ruff`, `ruff-format`, `mypy`, `lint-imports`, `bandit`, `pip-audit`,
   `conventional-pre-commit`) are unchanged. If lane fakes-ci-no-services has added comments to these
   hooks, keep them.
4. **`tests/meta/test_hooks_route_tests_through_the_harness.py`**, module-level test functions
   (the reason `tests/meta/test_githooks_reach_the_framework.py:30-33` gives), loading the file with
   `yaml.safe_load`:
   - `test_every_test_run_goes_through_the_harness`: every hook in a `local` repo whose `entry`
     contains `pytest` starts with `uv run vibey test run`;
   - `test_the_plain_test_suite_hook_is_gone`: no hook id is `test-suite`;
   - `test_the_gates_match_ci`: the four `--gate` includes equal the four `--include='…'` globs of
     the `Gate 4a`–`Gate 4d` steps in `.github/workflows/ci.yml` (`:75-85`), read from the file,
     each at `=100`.

## Where to change
- `.pre-commit-config.yaml` (with `edit_file`) and the new meta test.

## Acceptance criteria
- [ ] `uv run pre-commit validate-config` passes.
- [ ] The meta tests pass.
- [ ] `uv run pre-commit run coverage-gates --hook-stage pre-push` exits 0 on a clean tree, and its first line reads `vibey test-harness: backend=local … executed` (or `reused`).

## Tests to write first (TDD)
- `tests/meta/test_hooks_route_tests_through_the_harness.py` (above).

## Checks the lane must run (all must pass)
    uv run pre-commit validate-config
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta tests/infrastructure/test_worktree_hooks.py
    (cd src/vibey_tools/gh && uv run python -m pytest -q -p no:cacheprovider)
    uv run pre-commit run coverage-gates --hook-stage pre-push

## Out of scope
- `.githooks/*` and vibey-gh's templates: ADR-0028's chain already reaches this file.
- CI (harness-T19).
- CHANGELOG.md, docs/ (CONTRIBUTING.md's hook section is the docs wave's), ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15-test-run-cli.
- **Files touched:** `.pre-commit-config.yaml`, `tests/meta/test_hooks_route_tests_through_the_harness.py` (new).
- **Shares a file with:** `.pre-commit-config.yaml` (fakes-ci-no-services adds comments; if it landed first, keep them and keep this lane's hook).
- **Must keep passing unchanged:** `tests/meta/test_githooks_reach_the_framework.py`, `tests/infrastructure/test_worktree_hooks.py`, the vibey-gh suite (`installed()` compares only `.githooks/commit-msg` and `.githooks/pre-push`, and neither changes), and the protected tests.
- **Registry (amendment A4):** nothing; no seam is declared.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Do not edit anything under `.githooks/`, nor vibey-gh's templates.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; the meta test only reads files.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
