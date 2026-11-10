# SP1-A CI Gate Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ci.yml` fail fast and be judged by one check: a `lint` job that every heavy job
waits for, one aggregate `ci-result` check that cannot go green with nothing run, and per-job
timeouts and token permissions that a meta test enforces.

**Architecture:** Three tasks, all inside `.github/workflows/ci.yml` and `tests/meta/`. Nothing
here changes what any job runs, only the order, the gate and the limits. Changing which checks
are REQUIRED on `develop` and `main` is a repository-settings change through `.vibey-gh.toml`
and a reconcile, and is deliberately NOT in this plan (see "Not in this plan").

**Tech Stack:** GitHub Actions YAML, pytest meta tests parsing the workflow with `yaml.safe_load`.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md` (SP1: CI-A, CI-B, CI-C),
PR #1867. Baseline: `docs/architecture/evidence/` from PR #1869 (SP0 Task 5).

## Global Constraints

- Work only in the worktree. Do not push, merge, or change any GitHub setting, branch protection,
  ruleset or required check. Do not trigger workflows.
- `ci.yml` is hand-written (not template-rendered); another workflow under
  `src/vibey_tools/gh/vibey_gh/templates/workflows/` changes only at its template, and this plan
  touches none.
- No job is removed, renamed, or has its steps changed, except `gates` losing the steps that move to
  `lint`. Existing check NAMES stay exactly as they are (`gates`, `No-loss property suite (10,000
  examples)`, `VS Code extension (${{ matrix.os }})`, `No skip markers`, `uv.lock is in sync with
  pyproject.toml`): required checks are matched by name.
- A skipped job must report "skipped", never be absent: no workflow-level `paths:` filter.
- Every `${{ }}` value reaches a shell through `env:`, never inside `run:` (injection rule).
- Configuration lives in TOML where the repository does that: the timeout table is
  `tests/meta/ci_job_limits.toml`.
- Commits are Conventional Commits ending `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Review Focus

1. `ci-result` fails when any needed job fails or is cancelled, and when `lint` fails; it passes only
   when every job in `needs` finished `success` or `skipped`, so a docs-only PR is not blocked.
2. Moving steps from `gates` to `lint` leaves every gate still run exactly once per workflow run.
3. A job added to `ci.yml` later but forgotten in `ci-result`'s `needs` fails a meta test, not CI silently.
4. A job given a `timeout-minutes` too low for its measured wall time would fail spuriously: limits
   are set from the SP0 baseline with headroom, never guessed.

---

### Task 1: The aggregate `ci-result` check

**Files:**
- Modify: `.github/workflows/ci.yml` (append job `ci-result`)
- Create: `tests/meta/test_ci_result_covers_every_job.py`

**Interfaces:**
- Produces: job id `ci-result`, `name: CI result`, `needs:` every other job in `ci.yml`,
  `if: always()`, `runs-on: ubuntu-latest`, one step that exits non-zero unless every needed job's
  result is `success` or `skipped`.

- [ ] **Step 1: Write the failing meta test** `test_ci_result_covers_every_job.py`, parsing `ci.yml`:
  - `test_ci_result_needs_every_other_job`: `set(jobs["ci-result"]["needs"]) == set(jobs) - {"ci-result"}`; on failure the message names the missing job ids (Review Focus 3).
  - `test_ci_result_runs_even_when_a_needed_job_fails`: `jobs["ci-result"]["if"] == "always()"`.
  - `test_ci_result_step_fails_on_failure_and_cancellation_but_not_skip`: take the step's `run` script text and EXECUTE it with `bash` in a temp dir, passing the needed jobs' results through the `NEEDS_JSON` environment variable (see the Step 3 contract): assert exit 0 for `{"a":"success","b":"skipped"}`, exit 1 for `{"a":"failure"}`, exit 1 for `{"a":"cancelled"}`, exit 1 for a result string it does not know (`"weird"`), and exit 1 when `NEEDS_JSON` is empty or `{}` (nothing ran must not pass: Review Focus 1).
  - `test_no_workflow_expression_is_interpolated_into_the_script`: `"${{" not in step["run"]`.
- [ ] **Step 2: Run it and confirm it fails** (no `ci-result` job):
  `uv run pytest tests/meta/test_ci_result_covers_every_job.py -q -p no:cacheprovider -n0`
- [ ] **Step 3: Add the job.** The step's `env` has `NEEDS_JSON: ${{ toJSON(needs) }}`; the script is
  `python3 - <<'PY'` reading `os.environ["NEEDS_JSON"]`, which is a JSON object of
  `{job: {"result": ..., "outputs": ...}}`; it prints one line per job and exits 1 unless every
  `result` is `success` or `skipped` and the object is non-empty. Use `python3`, not `jq`, so the
  logic is unit-testable the same way in the meta test (pass the environment the same shape).
- [ ] **Step 4: Run the meta test and the workflow parse check**:
  `uv run pytest tests/meta -q -p no:cacheprovider -k "ci_ or workflow"` and `actionlint .github/workflows/ci.yml` if installed (say if not).
- [ ] **Step 5: Commit:** `git commit -m "ci: one aggregate result check that fails on any failed, cancelled or missing job"`

---

### Task 2: A `lint` job that every heavy job waits for

**Files:**
- Modify: `.github/workflows/ci.yml` (add job `lint`; change `needs` of the heavy jobs; remove the
  moved steps from `gates`)
- Modify: `tests/meta/test_ci_result_covers_every_job.py` (extend, no new file)

**Interfaces:**
- Consumes: Task 1's `ci-result` `needs` rule (a new job must be added to its `needs`).
- Produces: job id `lint`, `name: Lint and static gates`, containing these steps moved verbatim from
  `gates` in this order: setup (checkout, uv, python, install, node, TypeScript compiler), `Gate 0a`
  (TypeScript artifacts), `Gate 0` (corpus index), `Gate 1` (ruff check), `Gate 2` (ruff format),
  `Gate 3` (mypy --strict), and `Gate 5` (lint-imports). `uv-lock` stays its own job and stays first.

- [ ] **Step 1: Write the failing tests** (extend the meta file): `lint` exists and `needs: [uv-lock]`;
  every job that currently has `needs: [uv-lock]` (`gates`, `noloss`, `postgres-compatibility`,
  `tools`, `tools-lint`) now has `lint` in its `needs`; jobs with no `needs` today
  (`krypton-app`, `vibey-core`, `app`, `vscode-extension`, `desktop`, `image`, `chart`,
  `cluster-smoke`) have `lint` too, EXCEPT that this is a judgement the implementer must justify in the
  report: a JS-only job gains nothing from waiting on Python lint, so apply `lint` to the jobs that
  run Python or the container (`gates`, `noloss`, `postgres-compatibility`, `tools`, `tools-lint`,
  `image`, `cluster-smoke`) and leave the JS and desktop jobs ungated (they have their own typecheck).
  Assert that exact set. Assert each moved step name appears in `lint` and NOT in `gates` (Review
  Focus 2) and that no step name appears in both. Assert `gates` still contains Gates 4a to 4d,
  `Run test suite with coverage`, 6 and 7.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Move the steps** with no edit to their commands, add the `lint` job, add `lint` to
  the listed jobs' `needs`, and add `lint` to `ci-result`'s `needs`. The `gates` job keeps its
  `Install dependencies` and `Set up Python` steps (it still runs pytest and needs the environment);
  duplicating setup in `lint` is expected and is the cost of parallel gating.
- [ ] **Step 4: Run the meta tests, `actionlint`, and confirm `git diff --stat` shows only
  `ci.yml` and the meta test.** Report how many job-minutes `lint` adds to a green run (estimate
  from the baseline's step timings if present, else say unknown).
- [ ] **Step 5: Commit:** `git commit -m "ci: run the cheap static gates first so a lint failure stops the fan-out"`

---

### Task 3: Timeouts and token permissions, enforced

**Files:**
- Modify: `.github/workflows/ci.yml` (`timeout-minutes` on every job; top-level `permissions`)
- Create: `tests/meta/ci_job_limits.toml`, `tests/meta/test_ci_job_hygiene.py`

**Interfaces:**
- Produces: `ci_job_limits.toml` mapping each `ci.yml` job id to `timeout_minutes`, plus a
  `default_timeout_minutes`; a top-level `permissions: {contents: read}` in `ci.yml` with no job
  needing more (verify: no job writes, comments, or uses OIDC; if one does, it gets its own
  `permissions:` and the report says which).

- [ ] **Step 1: Write the failing tests** in `test_ci_job_hygiene.py`: every job in `ci.yml` has a
  `timeout-minutes` equal to its entry in the TOML (or the default when absent); a job in the
  workflow missing from the TOML fails naming it; a TOML entry for a job that no longer exists fails
  (the list shrinks when its reason goes, 12.e); `ci.yml` has a top-level `permissions` whose value is
  exactly `{"contents": "read"}` unless the TOML declares an exception list; and `actions/checkout`
  steps keep `persist-credentials: false` where the workflow already sets it (do not require it where
  it is absent: report which jobs lack it as a deferred observation).
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Choose the limits from measurement, not guesswork.** Read the committed baseline
  (`docs/architecture/evidence/ci-cost-baseline-*.json` if SP0 has merged; otherwise
  `gh api` GETs of 5 recent successful runs per job) and set each job's limit to the larger of
  `2 x observed p90 minutes` and `10`, rounded up to 5; cluster-smoke and image keep their existing 45.
  Put each value and the observed p90 it came from in a TOML comment beside it. Add the
  `timeout-minutes` lines and the `permissions` block to `ci.yml`.
- [ ] **Step 4: Run the meta tests and `actionlint`.** State in the report any job whose observed p90
  is within 50% of its new limit (Review Focus 4).
- [ ] **Step 5: Commit:** `git commit -m "ci: declare every job's time limit and the least token permission, and test both"`

---

## Not in this plan (needs the operator)

- **Making `ci-result` a required check, and removing the five checks it replaces,** is a
  branch-protection/ruleset change through `.vibey-gh.toml` `required_checks` and
  `vibey-gh reconcile`. Until it is applied, `ci-result` runs and reports but gates nothing. Applying
  it changes who can merge and is the operator's decision; the same reconcile is where the
  merge-queue enforcement (SP0 Decision 2) is applied.
- Path filters and the change-area map (CI-F), tiers (CI-F to CI-G), sharding, caches, native arm64,
  SBOM and SHA-pinned actions are later SP1 plans; each edits `ci.yml` and is queued after this one.
