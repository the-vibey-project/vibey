# SP4-B Tenant Static Strength Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the three tenants whose type checking is weaker than the root (`vibey_gh`, `vibey-skills`, `vibey_bootstrap`) to `mypy --strict`, so that "type-checked" in the SP4-A census means the same thing everywhere.

**Architecture:** Measured on the SP4-A branch (`mypy --strict --explicit-package-bases`, run from each tenant directory): `vibey_gh` 129 errors in 16 files (83 in `cli.py`), `vibey-skills` 5 in 2 files, `vibey_bootstrap` 52 in 24 files. `runners-common` is already `strict = true`. Fix the code, then flip each tenant's `[tool.mypy]` to `strict = true` so CI holds the line. Coverage floors, the root `bootstrap.py` gate, `tui/`, `.importlinter`, the suppression census, TypeScript and C flags and stale facts stay in later SP4 plans.

**Tech Stack:** Python 3.12, mypy 2.3, each tenant's own pyproject and CI `tools` matrix row (`static` key).

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md`, section SP4 ("Tenants to root strength"). Depends on SP4-A (#1893): the census's "type-checked" claim is only honest after this plan.

## Global Constraints

- Behaviour is unchanged: fix types, not logic. A real defect the types reveal gets its own commit, failing test first.
- No `# type: ignore`, `# noqa` or new `Any` without a same-line reason (the SP4 suppression census will count them).
- `vibey_bootstrap` keeps `warn_unused_ignores = false` (its lazy-import `type: ignore[import-not-found]` sites are needed downstream, see its pyproject comment); every other strict flag is enabled.
- Each tenant keeps its own floor: `vibey_gh` 100% coverage must not fall (`--cov-fail-under=100`), bootstrap `fail_under = 100`.
- Each tenant's own suite passes unchanged; dev-env-only extras are not made runtime requirements.
- Conventional Commits; no `--no-verify`; commit and push in the foreground; log hook output to a file. A PR touching shipped code needs a `changelog.d/<slug>.<type>.md` fragment.
- Any change to a tenant's CI `static` command goes through the single owner of `ci.yml` (SP1): keep it in one commit and name it in the PR.

## Review Focus

1. A fix that silently changes runtime behaviour (a `cast` hiding a real `None`, `Mapping` to `dict` copies, a narrowed `except`).
2. The tenant CI `static` step runs exactly the command whose zero-error result was measured (same paths, same `--explicit-package-bases`).
3. `vibey_gh`'s 100% coverage still holds when new branches (for example a `None` guard) are added: every new branch has a test.
4. `vibey_gh/templates/runner/egress/egress_gate.py` is rendered into other repositories; its types must not add imports the rendered target lacks.
5. Bootstrap's optional extras (`fastapi`, `apscheduler`, Azure, OpenTelemetry) stay optional: no new hard import.

---

### Task 1: `vibey-skills` strict (5 errors, 2 files)

**Files:** the 2 files named by `cd src/vibey_tools/skills && python -m mypy --strict --explicit-package-bases src`; `src/vibey_tools/skills/pyproject.toml` (`[tool.mypy]`).

**Interfaces:** Produces: a declared `[tool.mypy] strict = true` table for vibey-skills; Task 4 adds its CI step.

- [ ] **Step 1:** Add `[tool.mypy]` with `python_version = "3.12"` and `strict = true`; run the command above; record the 5 errors in the task report.
- [ ] **Step 2:** Fix them with precise annotations; no `Any` or `cast` without a same-line reason.
- [ ] **Step 3:** Run the tenant's own checks (`python3 tools/validate_manifests.py`, `python3 tools/check_links.py`, `PYTHONPATH=src python3 -m unittest discover -s tests`); expect pass.
- [ ] **Step 4:** Commit `refactor(skills): type vibey-skills for mypy --strict`.

### Task 2: `vibey_bootstrap` strict (52 errors, 24 files)

**Files:** the 24 files named by `cd src/vibey_tools/bootstrap && python -m mypy --strict --explicit-package-bases vibey_bootstrap` (most: `transports/sql.py` 6, `db/migrations/__init__.py` 6, `db/outbox.py` 5, `auth/webhook.py` 4); `src/vibey_tools/bootstrap/pyproject.toml` (`[tool.mypy]`, lines 359-372).

**Interfaces:** Produces: `disallow_untyped_defs = true`, `disallow_incomplete_defs = true` (or `strict = true` with `warn_unused_ignores = false` kept and its comment preserved).

- [ ] **Step 1:** Record the 52 errors in the task report; group by module.
- [ ] **Step 2:** Fix file by file, running mypy after each. Lazy-import sites keep their `type: ignore[import-not-found]`; add the reason where it is missing.
- [ ] **Step 3:** If an error reveals a real defect, stop, write a failing test, fix it in its own commit.
- [ ] **Step 4:** Flip the `[tool.mypy]` table to strict; run `pytest test/ -m "not integration" --cov=vibey_bootstrap` (from the tenant directory); expect pass at 100%.
- [ ] **Step 5:** Commit per module group: `refactor(bootstrap): type <modules> for mypy --strict`.

### Task 3: `vibey_gh` strict (129 errors, 16 files)

**Files:** the 16 files named by `cd src/vibey_tools/gh && python -m mypy --strict --explicit-package-bases vibey_gh`; `cli.py` 83, `merge_train.py` 10, `config.py` 10, `failover.py` 8, `templates/runner/egress/egress_gate.py` 7, `local_review.py` 5, `debugging.py` 4, `promote.py` 3, and one each in `reconcile`, `tidy`, `realign`, `local_authority`, `interfaces/__init__`, `fitloop`, `fit`, `corpus`; `src/vibey_tools/gh/pyproject.toml` (`[tool.mypy]`, line 147).

**Interfaces:** Produces: `strict = true` in vibey_gh's `[tool.mypy]`; `vibey-gh`'s black and isort gates still pass (it enforces both besides ruff-format).

- [ ] **Step 1:** Record the 129 errors; group `cli.py` by cause (untyped argparse handlers, `Namespace` attribute access, untyped returns).
- [ ] **Step 2:** Fix the small files first, then `cli.py` in groups of related commands, one commit per group. Prefer typed handler signatures and `TypedDict`/`Protocol` over `Any`.
- [ ] **Step 3:** Every new `None` guard or branch gets a test in the same commit so the 100% floor holds (Review Focus 3).
- [ ] **Step 4:** For `egress_gate.py`, confirm the rendered copy test (`tools-lint` drift check) still passes (Review Focus 4).
- [ ] **Step 5:** Run `python -m pytest -q`, `python -m black --check vibey_gh test`, `isort --check-only vibey_gh test`, `python -m mypy vibey_gh` (tenant directory); expect pass.
- [ ] **Step 6:** Commit per group: `refactor(gh): type <files> for mypy --strict`.

### Task 4: CI runs each tenant at strength and the census says so

**Files:** `.github/workflows/ci.yml` (`tools` matrix rows' `static` key for vibey_gh, vibey-skills, vibey_bootstrap); `tests/meta/ungated_python.toml` only if an entry's reason mentions looser tenant checking; `docs/agents/instructions.toml` and its rendered copies if they name the tenants' mypy strength.

**Interfaces:** Consumes: the three strict tables from Tasks 1 to 3.

- [ ] **Step 1 (test):** Add `tests/meta/test_tenant_mypy_is_strict.py`: for every tenant `pyproject.toml` that has a `[tool.mypy]` table, assert `strict = true` or the explicit allow-list in the test file (bootstrap's `warn_unused_ignores = false`, with its reason). Expect FAIL before Tasks 1 to 3 land, pass after.
- [ ] **Step 2:** Make each tenant row's `static` run mypy over the exact paths measured above (vibey-skills and vibey_bootstrap rows currently run none; vibey_gh runs `mypy vibey_gh` in `tools-lint`).
- [ ] **Step 3:** Run the tenant commands locally as CI does (CLAUDE.md "CI job `tools`" lines); expect 0 errors; run `uv run pytest tests/meta -q -p no:cacheprovider`; expect pass.
- [ ] **Step 4:** Commit `ci(tools): hold vibey_gh, vibey-skills and vibey_bootstrap to mypy --strict`.

### Final: whole-branch review on the most capable model, then push (10 to 12 minutes, foreground, log to a file), open the PR with measured before/after (129 to 0, 52 to 0, 5 to 0) and wait for the user's approval and queueing.
