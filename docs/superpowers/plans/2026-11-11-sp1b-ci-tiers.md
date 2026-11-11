# SP1-B CI Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop running every one of the 47 jobs on every PR. A feature PR into `develop` runs only
what its diff can affect, on a small matrix; the full matrix runs at the merge queue, at promotion
(develop to main), on push to `main` and, once the operator approves it, nightly on the develop tip.

**Architecture:** Four pieces that land and revert on their own: (1) a tested `vibey-gh` command
that turns a diff into changed areas and tier from a TOML map; (2) a `plan` job in `ci.yml` that
publishes the areas, the tier and ready-made matrices as job outputs and skips NOTHING; (3) the jobs
consume the outputs through job-level `if:` and `fromJSON` matrices; (4) the nightly, operator-gated.

**Tech Stack:** Python 3.12 (`vibey_gh`), GitHub Actions YAML (`fromJSON`, job outputs, job-level
`if:` and `continue-on-error`), pytest meta tests.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md` (SP1: CI-F, CI-G) and the
operator decisions of 2026-11-10 (develop push: core plus nightly extended; PR matrix reduced).
Evidence: `docs/architecture/evidence/ci-cost-baseline-*.json`, `tests/meta/ci_job_limits.toml`.

This plan was critiqued before any implementation; its first draft had these defects, now fixed
below: a failed `plan` job would have skipped the required `gates` and `noloss` (a skipped required
check passes); `docs`, `tools` and `deploy` changes were allowed to skip root `gates` although 67, 18
and 23 root test files read those trees; "covers every tracked file" contradicted "unmapped means
full"; four existing meta tests read a literal matrix; an empty `tools` matrix would abort the run.

## Global Constraints

- **A skipped required check passes on GitHub, so skipping must depend on the DIFF only.** Any job
  whose result is a REQUIRED check, or that guards one, is skipped only by an `if:` over
  `needs.plan.outputs.*`; the `plan` job itself can never cause a skip: it runs with job-level
  `continue-on-error: true`, its FIRST step writes `full=true`, `tier=full` and default full matrices
  to `$GITHUB_OUTPUT`, and later steps overwrite them. A `plan` failure, timeout or cancellation
  therefore yields `full`. A meta test proves every dependant's `if:` evaluates true when the outputs
  are the defaults. This replaces the unworkable "treat a failed plan as full" wording of the first
  draft: GitHub adds an implicit `success()` to any job with `needs`, so a dependant of a FAILED job is
  skipped before its `if:` is read; `continue-on-error` is what keeps `plan` from ever failing.
  **Unproven until Task 2 step 5:** that a job-level `continue-on-error` job reports `success` to its
  dependants and keeps the outputs an earlier step wrote after a later step fails, times out or is
  cancelled, is GitHub's documented behaviour but has NOT been observed here. If step 5 shows otherwise,
  stop: the design needs a different guard (for example computing the tier inside each dependant) before
  anything is allowed to skip.
- No job reads another job's `result` in an `if:`, except `lint` and `uv-lock` (the existing implicit
  `success()` chain). No job uses `always()`: a `lint` failure must still skip the heavy jobs.
- **Root `gates` is the one suite that reads the whole repository** (67 root test files read `docs/`,
  65 `scripts/`, 23 `deploy/`, 18 the tenants, 10 `clients/`). It therefore runs on EVERY diff except
  one that touches nothing in those trees (in practice: always). Only `noloss`, `postgres-compatibility`,
  `image`, `cluster-smoke`, the tenant matrix and the client jobs may skip by area.
- `Lint and static gates`, `uv-lock`, `plan` and `ci-result` always run.
- No workflow-level `paths:` filter. No ruleset or required-check change in this plan: if one is
  needed, stop and ask the operator (a ruleset also auto-applies after a successful develop Release).
- The full matrix is never lost, only moved: it runs on `merge_group`, on `pull_request` into `main`,
  on `push` to `main`, on `workflow_dispatch`, and on any change to `.github/**`, `scripts/**`,
  `pyproject.toml`, `uv.lock`, `.node-version`, `package.json`, `package-lock.json`, `.importlinter`,
  `.python-version`, `.vibey-gh.toml`, `design/**`, `research/**`, `changelog.d/**`, the agent trees
  (`.claude/**`, `.agent*/**`, `.cursor/**`, `.githooks/**`, `.vibey/**`) and the area map.
  Anything that matches no area is `full` (fail safe); the config test asserts every tracked file is
  either mapped or covered by `[full]`, so an unmapped file is a defect found by a test, not a runtime
  surprise.
- Area membership is TOML read by tested code, never inline bash. The area map and the matrices are
  each ONE source (`.github/ci-areas.toml`, `.github/ci-matrices.toml`).
- Job ids and check names do not change, except the two VS Code jobs in Task 3 step 4.
- Every `${{ }}` reaches a shell through `env:`. Commits are Conventional Commits ending
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- The nightly is a NEW scheduled trigger and every scheduled workflow is currently
  `disabled_manually`; Task 4 is operator-gated.

## Review Focus

1. **Fail safe.** An unmapped file, an empty diff, a diff that cannot be computed, a failed or timed-out
   `plan`, a missing output, or an event the code does not recognise results in `full`.
2. **Required checks never go missing.** On every kind of PR each required check is run or reported
   `skipped` under its exact name; the two VS Code names in particular.
3. **A moved matrix row still runs somewhere.** Every row the PR tier drops is in the full tier, and the
   four existing matrix-reading meta tests, repointed at the full tier, are the permanent guard.
4. **`plan` is cheap and boring**: one Linux job, installs only `vibey-gh`, target under a minute.
5. **No empty matrix ever reaches `strategy`**: an empty row set is turned into a skipped job by a
   boolean output, never into `fromJSON` of an empty `include`.
6. **Event field names are NOT verified by tooling** (`actionlint` accepted a deliberately fake
   `github.event.merge_group` field). `merge_group.base_sha`/`head_sha` rest on documentation, and the
   repository has NEVER had a `merge_group` run (`gh run list --event merge_group` is empty for every
   workflow). The first merge-queue run of Task 2's `plan` job is the proof; read its summary and record
   the base and head it used. Task 3 must not merge before that, and Task 2 must not be admin-merged.

---

### Task 1: `vibey-gh ci-areas` and `ci-matrix`: a diff becomes areas, tier and matrices

**Files:**
- Create: `.github/ci-areas.toml`, `.github/ci-matrices.toml`
- Create: `src/vibey_tools/gh/vibey_gh/ci_areas.py`, `src/vibey_tools/gh/vibey_gh/interfaces/ci_areas_interface.py`
- Modify: `src/vibey_tools/gh/vibey_gh/cli.py` (register both subcommands the way `rulesets` is registered)
- Test: `src/vibey_tools/gh/test/test_ci_areas.py`

**Interfaces:**
- Produces:
  - `AreaDecision` (frozen dataclass): `areas: frozenset[str]`, `full: bool`, `reasons: tuple[str, ...]`.
  - `CiAreasInterface` (Protocol): `classify(self, paths: Sequence[str], *, event: str, base_ref: str) -> AreaDecision`
    and `matrix(self, job: str, decision: AreaDecision) -> Mapping[str, Any]`.
  - `CiAreas(areas: Mapping[str, Any], matrices: Mapping[str, Any])` implementing it.
  - CLI `vibey-gh ci-areas --base <sha> --head <sha> --event <name> --base-ref <ref> [--format github-output|json]`:
    runs `git diff --name-only --no-renames -z <base>...<head>` (three-dot, so a PR behind its base is not
    charged with the base's newer changes) through the family's existing command runner (do not call
    `subprocess` ad hoc), and prints for `$GITHUB_OUTPUT`: `areas=<json list>`, `full=<true|false>`,
    `tier=<pr|full>`, `tools_any`, `postgres_any`, `desktop_any`, and one `<job>_matrix=<json>` per matrix
    job. Any failure of git, an unknown event, or an empty diff prints the all-full defaults and exits 0.
  - `merge_group`, `workflow_dispatch`, `schedule`, a `pull_request` whose `--base-ref` is `main`, and a
    `push` to `main` are `full` by event; the CLI learns the base branch from `--base-ref`.
- Config (`.github/ci-areas.toml`): `[areas.<name>] paths = [fnmatch globs where ** crosses /]`:
  - `python`: `src/vibey/**`, `tests/**`
  - `tools`: `src/vibey_tools/**`, `src/vibey_runners/**`
  - `vscode`: `clients/vscode/**`; `packages/vibey-core/**` maps to `vscode` AND `app` (a core change
    affects both consumers); `app`: `clients/app/**`; `krypton_app`: `clients/krypton-app/**`
  - `desktop`: `clients/desktop/**`
  - `deploy`: `deploy/**`
  - `docs`: `docs/**`, `docs-src/**`, `docs-theme/**`, `properdocs.yml`, and the ROOT markdown by
    exact name only: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CHANGELOG.md`,
    `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`
  - `[full] paths`: the always-full list in Global Constraints.
- Config (`.github/ci-matrices.toml`): per matrix job (`tools`, `postgres-compatibility`, `desktop`) a
  `full` row list (exactly today's rows, copied from `ci.yml` at the base commit) and a `pr` row list.
  `tools` PR tier: each of the 7 packages at Python 3.12 on ubuntu (7 rows), filtered to the packages whose
  directory changed; when the `tools` area changed only through a path that no package owns, or the diff is
  `python`-only, the rule is: **a `python`-area-only PR runs all 7 PR-tier rows** (the tenants depend on the
  root package), a `tools`-area PR runs the rows of the changed packages (a path under `src/vibey_tools/gh`
  selects `vibey-gh`, and so on; an unowned path under `src/vibey_tools` or `src/vibey_runners` selects all
  7). `postgres-compatibility` PR tier: 14 and 18. `desktop` PR tier: ubuntu only.

- [ ] **Step 1: Write the failing tests:**
  - `test_a_docs_only_diff_yields_docs_and_tier_pr` (`["docs/guides/x.md"]`).
  - `test_python_source_yields_python`; `test_a_tenant_path_yields_tools_and_selects_only_its_package_row`
    (`src/vibey_tools/gh/vibey_gh/x.py` yields the `vibey-gh` row only); `test_a_core_change_yields_vscode_and_app`.
  - `test_each_always_full_path_forces_full`, parametrised over every entry of `[full]` and over
    `.github/workflows/ci.yml`, `scripts/x.py`, `.claude/skills/x/SKILL.md`, `package.json`.
  - `test_an_unmapped_file_forces_full_with_a_reason_naming_it`, `test_an_empty_diff_forces_full`.
  - `test_each_full_event_forces_full`: `merge_group`, `workflow_dispatch`, `schedule`, a pull request into
    `main`, a `push` with base ref `main`; and `test_an_unknown_event_forces_full`.
  - `test_the_repository_config_covers_every_tracked_file`: load the real TOML files, list `git ls-files`,
    assert every file is matched by an area or by `[full]`; the failure message names up to 10 files.
  - `test_the_union_of_pr_and_full_rows_is_the_full_set_and_pr_rows_are_a_subset`.
  - `test_an_empty_row_set_prints_the_any_output_false_and_no_matrix` (Review Focus 5).
  - `test_the_cli_prints_github_output_lines_and_defaults_to_full_when_git_fails` (fake runner returns
    non-zero: output is the all-full defaults, exit status 0), and `test_the_diff_command_is_three_dot_no_renames_z`.
- [ ] **Step 2: Run them and confirm they fail** (`cd src/vibey_tools/gh && python -m pytest -q test/test_ci_areas.py`).
- [ ] **Step 3: Implement.** Keep the tenant's own gates (read the `vibey-gh` row of `ci.yml`): its static
  gates and coverage floor; every new line is covered.
- [ ] **Step 4: Run the tenant's suite and static gates as its `ci.yml` row runs them**, ruff on touched files.
- [ ] **Step 5: Commit:** `git commit -m "feat(gh): turn a diff into changed CI areas, a tier and matrices from declared maps"`

---

### Task 2: A report-only `plan` job (merge it through the queue, never by admin)

**Files:**
- Modify: `.github/workflows/ci.yml` (add job `plan`; add it to `ci-result.needs`)
- Modify: `tests/meta/ci_job_limits.toml`, `tests/meta/test_ci_result_covers_every_job.py` (classification: `plan` is neither
  gated nor ungated; extend the partition, do not weaken it)
- Test: `tests/meta/test_ci_plan_job.py` (new)

**Interfaces:**
- Consumes: Task 1's CLI.
- Produces: job `plan`, `name: CI plan`, ubuntu, `timeout-minutes: 10`, `continue-on-error: true`, no `needs`,
  outputs `areas`, `full`, `tier`, `tools_any`, `postgres_any`, `desktop_any`, `tools_matrix`,
  `postgres_matrix`, `desktop_matrix`. Step 1 writes the all-full defaults. Step 2 checks out with
  `fetch-depth: 0` (a shallow clone cannot diff). Step 3 installs only `vibey-gh` from the checkout and runs
  `vibey-gh ci-areas` with per-event arguments, all via `env:`:
  `pull_request`: base `github.event.pull_request.base.sha`, head `github.event.pull_request.head.sha`,
  base ref `github.event.pull_request.base.ref`; `push`: base `github.event.before` (an all-zero value
  means a new branch: `full`), head `github.sha`, base ref `github.ref_name`; `merge_group`: base
  `github.event.merge_group.base_sha`, head `github.event.merge_group.head_sha`; `workflow_dispatch` and
  `schedule`: `full`. It writes the decision and its reasons to `$GITHUB_STEP_SUMMARY`.
  **It skips nothing in this task: no other job reads its outputs yet.**

- [ ] **Step 1: Write the failing meta tests:** `plan` exists, has no `needs`, has `continue-on-error: true`, has the
  listed outputs, has a limits entry, is in `ci-result.needs`; the first step writes the all-full defaults
  (assert `full=true` and `tier=full` appear before the `vibey-gh` step); no `${{` in any `run`; the checkout is
  `fetch-depth: 0`; and, by executing the step's shell with sample `env:` and a stub `vibey-gh` on `PATH` that echoes its
  arguments, the arguments for each of the five events are exactly as specified (an all-zero `before` produces
  the `full` path without calling git).
- [ ] **Step 2: Run and confirm failure.**
- [ ] **Step 3: Add the job.** Measure and report how long `plan` takes (target: under a minute).
- [ ] **Step 4: Validate** with `actionlint` and the meta suite. Open the PR; its own run is the first proof: the job
  summary must show `full` because `ci.yml` changed. Put the observed values in the PR description.
- [ ] **Step 5: Prove the failure path.** Push a throwaway DRAFT branch (never merged) in which the `vibey-gh ci-areas` step is
  forced to `exit 1`; record from the run that `plan` is reported with `continue-on-error`, that `needs.plan.outputs.full`
  is `true`, and that `ci-result` is green. This is the evidence for the Global Constraint; without it Task 3 does not start.
- [ ] **Step 6: Commit:** `git commit -m "ci: a plan job reports the changed areas and the tier and can never cause a skip"`
- [ ] **Step 7: Merge through the merge queue, not by admin**, and record from the resulting `merge_group` run's `plan`
  summary the base and head SHAs it used (Review Focus 6).

---

### Task 3: Jobs consume the plan (the only task that changes what runs)

**Files:**
- Modify: `.github/workflows/ci.yml` (job-level `if:`; `fromJSON` matrices; the VS Code jobs)
- Modify: `tests/meta/test_postgres_support_matrix.py`, `tests/meta/test_tools_matrix_covers_every_package.py`,
  `tests/meta/test_krypton_linux_flavors.py`, `tests/meta/test_supported_platforms_have_ci.py` (each reads a literal
  `strategy.matrix` today; repoint them at the FULL rows in `.github/ci-matrices.toml`: they become the permanent
  no-dropped-row guard)
- Modify: `.github/workflows/automation-bootstrap.yml` (require `success`, not `skipped`, for `gates`)
- Modify: `tests/meta/ci_job_limits.toml`, `tests/meta/test_ci_result_covers_every_job.py` (job ids for Task 3 step 4)
- Create: `tests/meta/ci_matrix_snapshot.json`, `tests/meta/test_ci_tiers_keep_every_row.py`

**Interfaces:**
- Consumes: Task 2's outputs.
- Produces, in `ci.yml`, with `needs: [..., plan]` added to each job below (keep the existing `needs`):
  - `gates`: no area `if:` (always runs).
  - `noloss`, `postgres-compatibility`: `if: needs.plan.outputs.full != 'false' || contains(fromJSON(needs.plan.outputs.areas), 'python')`
    plus `tools`/`deploy`/`docs` do not trigger them. `postgres-compatibility` also needs `postgres_any != 'false'`.
  - `tools`, `tools-lint`: `full != 'false' || tools or python in areas`; `tools` also `tools_any != 'false'`.
  - `image`, `cluster-smoke`, `chart`: `full != 'false' || python or tools or deploy in areas` (the Dockerfile copies the
    tenant sources, `deploy/docker/Dockerfile:135-144`).
  - `krypton-app`: `krypton_app`; `vibey-core`, `app`: `vscode` or `app`; `desktop`: `desktop`; each also `full != 'false'`.
  - A docs-only PR therefore runs `uv-lock`, `plan`, `lint`, `gates`, `ci-result` and the always-on checks, and skips the rest.
  - Matrices: `strategy.matrix: ${{ fromJSON(needs.plan.outputs.<job>_matrix) }}` for `tools`, `postgres-compatibility`,
    `desktop`, each guarded by its `<job>_any` output so an empty set never reaches `strategy`. `fail-fast` stays `false`;
    every `name:` template is unchanged.
- **Snapshot:** commit `tests/meta/ci_matrix_snapshot.json` generated from TODAY's `ci.yml` in a SEPARATE FIRST COMMIT, before
  `ci.yml` is edited, so a regenerated snapshot cannot hide a dropped row; the ongoing guard is the four repointed tests.

- [ ] **Step 1: First commit, the snapshot** of the current matrices (`tools` 24 rows, `postgres` 14 to 18, `desktop` 4 rows,
  `vscode` 2 rows). `git commit -m "test(meta): snapshot the CI matrices before they move"`.
- [ ] **Step 2: Write the failing tests** `test_ci_tiers_keep_every_row.py`: (a) union of PR and full rows per matrix job equals the
  snapshot; (b) every PR row is a member of the full rows; (c) every area `if:` references only `needs.plan.outputs`; (d) no
  `if:` reads another job's `result` or uses `always()`; (e) every job that gained an `if:` has `plan` in `needs`; (f) with the
  outputs set to the DEFAULTS (`full=true`) every dependant's `if:` evaluates true (evaluate the expressions with a small
  evaluator for the subset of the expression language used, or assert the exact expression strings: choose and say why);
  (g) `gates` has no area `if:`; (h) a `tools`-only diff does not skip `gates`; and repoint the four existing tests.
- [ ] **Step 3: Run and confirm failure.**
- [ ] **Step 4: The two REQUIRED VS Code checks, OPTION B.** Replace the matrix job with two non-matrix jobs whose `name:` is
  byte-identical to the required names: `VS Code extension (ubuntu-latest)` and `VS Code extension (macos-latest)`; each is
  skipped by `if: needs.plan.outputs.full != 'false' || vscode in areas`. A meta test asserts both literal names, that the job
  ids in `ci_job_limits.toml`, `ci-result.needs` and the lint-gating partition are updated, and that artifact names are
  unchanged. Evidence that a skipped MATRIX job reports its unexpanded template name: run 41614652612 (Release binaries,
  mode=skip). If option B cannot keep both names byte-identical, STOP and report.
- [ ] **Step 5: `automation-bootstrap.yml`:** require `conclusion == "success"` for `gates` (it accepts `skipped` today and then
  runs `gh pr merge --admin`); a test asserts the jq expression.
- [ ] **Step 6: Move the matrices** into `ci-matrices.toml`, add the `plan` outputs they need, edit `ci.yml`, and run the whole meta suite.
- [ ] **Step 7: First-run proof.** For FOUR constructed diffs record the `vibey-gh ci-areas` output and which jobs a PR would run
  and how many macOS jobs: docs-only, `src/vibey/`, `clients/vscode/`, `ci.yml`. State whether you ran four throwaway draft PRs
  (preferred; never merged) or ran the command locally against constructed diffs.
- [ ] **Step 8: Commit:** `git commit -m "ci: skip unchanged areas and run the small matrix on pull requests"`

---

### Task 4 (OPERATOR-GATED; not started without a yes): the nightly full run

A `schedule:` trigger or `ci-nightly.yml`. **Ask first:** (a) whether scheduled workflows are meant to be disabled (every one is
`disabled_manually` with no recorded reason), (b) who owns a red nightly (the master plan: it opens an issue through
`vibey-gh issue_automation` and skips when the develop tip is unchanged since the last green nightly, like
`release-binaries.yml`'s plan step), (c) the hour. Until then the full matrix runs at `merge_group`, promotion and
`push` to `main`, the minimum the approved design requires.

---

## Deliberate departures from the master plan

The master SP1 table sends `merge_group` to the PR tier and a develop push to the reduced set. This plan sends `merge_group` to
the FULL matrix (up to six macOS cells per queue entry): safer, because a PR tier that skips by area is proven green only
against the diff, and the queue is where a combined group is proven. Revisit once the queue has run and its cost is measured.

## Not in this plan

Sharding the root suite, native arm64, caches, SHA pinning, SBOM, a `docs` strict build job (CI-E, CI-H to CI-K): later sub-plans.
Any required-check or ruleset change (ask the operator).
