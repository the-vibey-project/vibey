# SP4-A Static-Gate Parity for scripts/ and the Storm Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the two largest ungated Python trees, `scripts/` (76 files) and `docs/plans/qwenstorm-3.0.0/tools/` (39 files, including the mandatory `push_gate.py`), under the same ruff and `mypy --strict` gates as `src/vibey`, and make a new ungated tracked `.py` file fail a census.

**Architecture:** Measured on `origin/develop` `30ce46b95`: ruff's `include` already lists `scripts/**/*.py` but not the storm tools (4 findings under the repo rules); `mypy --strict --explicit-package-bases` reports **100 errors in 18 files** on `scripts/` and **58 errors in 16 files** on the storm tools. Fix the code, add a mypy gate to the `lint` job for each tree, then add a `tests/meta` census that fails when a tracked `.py` file sits outside every gate's reach. Parts of SP4 not named here (tenant strength, suppression census, TypeScript and C flags, stale facts) stay in later SP4 plans.

**Tech Stack:** Python 3.12, ruff, mypy 2.3, GitHub Actions `ci.yml` `lint` job, pytest meta tests.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md`, section SP4 (Q1, Q5).

## Global Constraints

- No `# type: ignore`, `# noqa` or `Any` added without a same-line reason (the SP4 suppression census will count them).
- Behaviour of every script is unchanged: fix types, not logic. A real bug the types reveal gets its own commit, failing test first, and an issue if the fix is a design decision.
- `push_gate.py` is the push gate: its existing tests must pass unchanged, and a change to it is a separate commit.
- A path that cannot be named by the tool (dashed file names such as `lane-publish.py` are not importable modules) is checked by path, never renamed.
- Conventional Commits; no `--no-verify`; commit and push in the foreground; log hook output to a file.
- A PR changing shipped code needs a `changelog.d/` fragment; these trees ship nothing, so none is expected. If `Changelog fragment` still asks, add one.
- Everything configurable lives in `pyproject.toml`, not in the workflow.

## Review Focus

1. A mypy fix that silently changes runtime behaviour (a cast hiding a real `None`, `Mapping` to `dict` copies).
2. `push_gate.py` still blocks the same pushes it blocked before.
3. The census cannot be satisfied by adding a path to an ignore list with no written reason.
4. The mypy gate runs over exactly the files the census says it covers (no drift between the two lists).
5. Dashed script names are still type-checked.

---

### Task 1: Ruff reaches the storm tools

**Files:** Modify `pyproject.toml` (`[tool.ruff] include`); fix the 4 findings in `docs/plans/qwenstorm-3.0.0/tools/`.

**Interfaces:** Produces: `uv run ruff check .` and `ruff format --check .` cover `docs/plans/qwenstorm-3.0.0/tools/**/*.py`.

- [ ] **Step 1:** Add `"docs/plans/qwenstorm-3.0.0/tools/**/*.py"` to `include`. Run `uv run ruff check .`; expect exactly the 4 findings (`--isolated --select E,F,I,UP,B,SIM --ignore E501` reproduced them).
- [ ] **Step 2:** Fix them with `ruff check --fix` and review the diff for behaviour change. Run `uv run ruff format .` on the tree if `ruff format --check .` fails; the format-only change is its own commit.
- [ ] **Step 3:** Run the storm tools' tests (`tests/` files that import `push_gate`, `storm_*`; find with `grep -rl "qwenstorm-3.0.0/tools" tests`); expect pass.
- [ ] **Step 4:** Commit `build(lint): run ruff over the storm tools`.

### Task 2: `mypy --strict` clean on the storm tools (58 errors, 16 files)

**Files:** the 16 files named by `MYPYPATH=docs/plans/qwenstorm-3.0.0/tools uv run mypy --strict --explicit-package-bases docs/plans/qwenstorm-3.0.0/tools`; `pyproject.toml`.

**Interfaces:** Produces: a `[tool.mypy]`-adjacent, declared way to run mypy on this tree (a second config table or a documented command in `pyproject.toml`'s comment next to a new `[tool.vibey.static_gates]` list: `{name, paths, mypy_path}` entries). Task 3 and Task 4 consume that list.

- [ ] **Step 1:** Add the `[tool.vibey.static_gates]` list with one entry for the storm tools. Run mypy through it; record the 58 errors in the task report.
- [ ] **Step 2:** Fix file by file, running mypy after each. Prefer precise annotations and `TypedDict`/`Protocol` over `Any` and `cast`. A `cast` needs a same-line reason.
- [ ] **Step 3:** If an error reveals a real defect, stop, write a failing test, fix it in its own commit.
- [ ] **Step 4:** Run the storm tools' tests (Task 1, Step 3); expect pass, with `push_gate`'s tests untouched.
- [ ] **Step 5:** Commit per file group: `refactor(storm): type <files> for mypy --strict`.

### Task 3: `mypy --strict` clean on `scripts/` (100 errors, 18 files)

**Files:** the 18 files named by `uv run mypy --strict --explicit-package-bases scripts` (first: `scripts/autonomy_scorecard.py:720`, a `list[Mapping]` assigned to a `list[dict]`).

**Interfaces:** Consumes: the `[tool.vibey.static_gates]` list (add the `scripts` entry). Produces: zero mypy errors on `scripts/`.

- [ ] **Step 1:** Add the `scripts` entry; run it; record the 100 errors.
- [ ] **Step 2:** Fix by file, same rules as Task 2. Run the file's own test (`tests/` that imports it, or `tests/meta`) after each.
- [ ] **Step 3:** Run `uv run pytest tests/meta -q -p no:cacheprovider`; expect pass.
- [ ] **Step 4:** Commit per file group: `refactor(scripts): type <files> for mypy --strict`.

### Task 4: The gate runs in CI and a census prevents drift

**Files:** Modify `.github/workflows/ci.yml` (`lint` job), `.pre-commit-config.yaml`; Create `tests/meta/test_every_python_file_is_gated.py`.

**Interfaces:** Consumes: `[tool.vibey.static_gates]` and `[tool.ruff] include`. Produces: a census over `git ls-files '*.py'`.

- [ ] **Step 1 (test):** `test_every_tracked_python_file_is_under_ruff_and_mypy`: every tracked `.py` is under a ruff `include` glob and under a `static_gates` path, a tenant's own gated tree (read from `ci.yml` tools matrix `static`/`dir` keys), or an entry in `tests/meta/ungated_python.toml` with a non-empty `reason`. Expect FAIL if you first omit the storm tools' tests directory, then pass once listed. Also `test_ungated_python_baseline_only_falls` (the entry count may not exceed the committed `CEILING`) and `test_every_ungated_entry_has_a_reason`.
- [ ] **Step 2:** Make the `lint` job loop over `[tool.vibey.static_gates]` (a short Python step through the repo's own TOML reader, not inline bash parsing) running `mypy --strict --explicit-package-bases` with each entry's `mypy_path`. Mirror in `.pre-commit-config.yaml` only if the hook is cheap (measure: if over 30 s, leave it CI-only and say so in the PR).
- [ ] **Step 3:** Run `uv run python -c` equivalent of the lint step locally; expect 0 errors. Run `uv run pytest tests/meta/test_every_python_file_is_gated.py -q`; expect pass. Prove the census fails by adding a stray `scripts/../tmp_ungated.py` outside the lists (revert after).
- [ ] **Step 4:** Commit `ci(lint): gate scripts and the storm tools with mypy --strict and census every Python file`.

### Final: whole-branch review on the most capable model, then push (10 to 12 minutes, foreground, log to a file), open the PR with the measured before/after (100 to 0, 58 to 0, 4 to 0), and wait for the user's approval and queueing.
