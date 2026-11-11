# SP1-B CI Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop running every one of the 47 jobs on every PR. A feature PR into `develop` runs the
changed areas on a small matrix; the full matrix runs at promotion (develop to main), on the
merge queue, and nightly on the develop tip.

**Architecture:** Three pieces, each landing and reverting on its own: (1) a tested `vibey-gh`
command that turns a diff into changed areas from a TOML map; (2) a `plan` job in `ci.yml` that
runs it and publishes the areas and a tier as job outputs, still skipping NOTHING (report-only);
(3) the jobs consume the outputs: job-level `if:` for areas, and matrices computed with
`fromJSON` so one definition serves a small PR tier and the full tier. Piece 3 is the only one
that changes what runs.

**Tech Stack:** Python 3.12 (`vibey_gh`), GitHub Actions YAML (`fromJSON`, job outputs, job-level
`if:`), pytest meta tests.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md` (SP1: CI-F, CI-G),
operator decisions of 2026-11-10 (develop push: core + nightly extended; PR matrix reduced).
Evidence: SP0's baseline (`docs/architecture/evidence/ci-cost-baseline-*.json`) and SP1-A's
measured job durations (`tests/meta/ci_job_limits.toml`).

## Global Constraints

- **A skipped job must still satisfy its required check.** Required checks are matched by NAME.
  A job skipped at job level reports `skipped` under its template name; a MATRIX job skipped
  before expansion reports the unexpanded name (`VS Code extension (${{ matrix.os }})`), so the
  two required VS Code checks would never appear. Task 3 gives those two a safe path (see its
  step 4) and a meta test pins it.
- A skipped required check counts as PASSING on GitHub, so every skip rule must be a function of
  the diff only, never of an upstream job's failure. `ci-result` (SP1-A) stays the catch-all.
- No workflow-level `paths:` filter (a workflow that does not run leaves required checks
  "Expected" forever). The skipping is job-level `if:` driven by the `plan` job.
- The full matrix is NEVER lost, only moved: it must run on (a) `merge_group`, (b) pull requests
  into `main`, (c) push to `main`, (d) a nightly schedule on the develop tip, (e) any change to
  `ci.yml`, `pyproject.toml`, `uv.lock`, `.node-version`, `package-lock.json` or the area map
  itself (`full`).
- Area membership is declared in TOML (`.github/ci-areas.toml`), read by tested code; no
  path logic in inline bash. A changed file that matches NO area forces `full` (fail safe).
- Job ids and check names do not change except where a task says so. No ruleset or required
  check is changed by this plan; if one must change, stop and ask the operator (the ruleset also
  auto-applies after a successful develop Release: see the memory note on the apply chain).
- Every `${{ }}` reaches a shell through `env:`. Commits: Conventional Commits ending
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- The nightly schedule is a NEW trigger: scheduled workflows are currently disabled
  (`disabled_manually`), and a schedule runs only on the default branch. Task 4 is therefore
  operator-gated and is not started without a yes.

## Review Focus

1. **Fail safe.** An unmapped file, an empty diff, a diff that cannot be computed (shallow
   clone, force-push, first push), or a `plan` job failure results in `full`, never in skipping.
2. **Required checks never go missing.** On a docs-only PR every required check is either run or
   `skipped` under its exact required name; the two VS Code names in particular.
3. **A moved matrix row still runs somewhere.** Every row removed from the PR tier appears in the
   promotion/merge-queue/nightly tier, and a meta test proves the union of tiers equals today's
   full set (no row silently dropped).
4. **The plan job is cheap and boring.** One Linux job, seconds, no checkout of dependencies.
5. **Stale `merge_group` / `pull_request` event shapes**: `github.event.pull_request.base.sha`
   does not exist on `merge_group` or `push`; each event computes its base explicitly.
6. **The event field names are NOT verified by tooling.** `actionlint` does not validate
   `github.event.*` property names (a control probe with a deliberately fake field passed), so
   `github.event.merge_group.base_sha` / `head_sha` rest on GitHub's documentation alone. An empty
   or wrong value must widen to `full` (Review Focus 1), never skip, and the FIRST merge-queue run
   of Task 2's `plan` job is the proof: read its job summary and record the base and head it used.
   Until that run exists, Task 3 must not merge.

---

### Task 1: `vibey-gh ci-areas`: a diff becomes changed areas, from TOML

**Files:**
- Create: `.github/ci-areas.toml`
- Create: `src/vibey_tools/gh/vibey_gh/ci_areas.py`,
  `src/vibey_tools/gh/vibey_gh/interfaces/ci_areas_interface.py`
- Modify: `src/vibey_tools/gh/vibey_gh/cli.py` (register the subcommand; follow how a neighbour such as
  `branch-health` or `rulesets` is registered)
- Test: `src/vibey_tools/gh/test/test_ci_areas.py`

**Interfaces:**
- Produces:
  - `CiAreasInterface` (Protocol): `classify(self, paths: Sequence[str]) -> AreaDecision`.
  - `AreaDecision` (frozen dataclass): `areas: frozenset[str]`, `full: bool`, `reasons: tuple[str, ...]`.
  - `CiAreas(config: Mapping[str, Any])` implementing it.
  - CLI: `vibey-gh ci-areas --base <sha> --head <sha> [--event <name>] [--format github-output|json]`;
    it runs `git diff --name-only <base> <head>` through the family's existing command runner
    (reuse the runner in `vibey_gh`; do not call subprocess ad hoc), and prints either
    `areas=<json list>`, `full=<true|false>`, `tier=<pr|full>` lines for `$GITHUB_OUTPUT`, or JSON.
- Config shape (`.github/ci-areas.toml`):
  `[areas.<name>] paths = [globs]` for: `python` (src/vibey/**, tests/**, pyproject.toml excluded:
  those are `full`), `tools` (src/vibey_tools/**, src/vibey_runners/**), `vscode`
  (clients/vscode/**, packages/vibey-core/**), `app` (clients/app/**, packages/**), `krypton_app`
  (clients/krypton-app/**), `desktop` (clients/desktop/**), `deploy` (deploy/**, Dockerfile paths),
  `docs` (docs/**, *.md outside src, mkdocs/properdocs config: docs-only). `[full] paths` = the
  always-full triggers listed in Global Constraints. `[events] full = ["merge_group", "push-main",
  "pull_request-main"]`.

- [ ] **Step 1: Write the failing tests** (names and assertions):
  - `test_a_docs_only_diff_yields_only_the_docs_area`: `["docs/guides/x.md"]` gives `{"docs"}`, `full False`.
  - `test_a_python_source_change_yields_python`; `test_a_tenant_change_yields_tools`;
    `test_a_vscode_change_yields_vscode_and_core_consumers` (core change maps to `vscode` and `app`).
  - `test_each_always_full_path_forces_full`: parametrised over `.github/workflows/ci.yml`, `pyproject.toml`,
    `uv.lock`, `.node-version`, `package-lock.json`, `.github/ci-areas.toml`.
  - `test_an_unmapped_file_forces_full_with_a_reason`: `["some/new/dir/x.bin"]` gives `full True` and the
    reason names the path (Review Focus 1).
  - `test_an_empty_diff_forces_full`: `[]` gives `full True` (a diff that could not be computed must not skip).
  - `test_event_forces_full`: parametrised over `merge_group` and a PR into main.
  - `test_the_toml_in_the_repository_loads_and_covers_every_tracked_file`: load the real
    `.github/ci-areas.toml`, list every tracked file (`git ls-files`) and assert each file matches at least
    one area or `[full]`, otherwise fail naming up to 10 unmapped files (an unmapped tracked file is a
    config defect, not a runtime surprise).
  - `test_the_cli_prints_github_output_lines`: fake the runner returning a diff; assert the three lines.
  - `test_the_cli_exits_zero_and_says_full_when_git_fails`: runner returns non-zero; output `full=true`,
    exit 0 (the job must not fail; it must widen).
- [ ] **Step 2: Run them and confirm they fail** (`cd src/vibey_tools/gh && python -m pytest -q test/test_ci_areas.py`).
- [ ] **Step 3: Implement** `CiAreas.classify` (glob matching with `fnmatch` semantics where `**` crosses
  directories; first compute `full` triggers, then areas) and the CLI wrapper. Keep the tenant's own floors:
  vibey-gh runs `mypy` (strict as of the SP4 plan; at least the current config) and its coverage gate:
  every new line must be covered.
- [ ] **Step 4: Run the tenant suite portion and its static gates** as the `vibey-gh` row of `ci.yml` runs them
  (read the row; do not guess), plus ruff on the touched files.
- [ ] **Step 5: Commit:** `git commit -m "feat(gh): turn a diff into changed CI areas from a declared map"`

---

### Task 2: A report-only `plan` job

**Files:**
- Modify: `.github/workflows/ci.yml` (add job `plan`; add it to `ci-result` needs; add its limit)
- Modify: `tests/meta/ci_job_limits.toml`, `tests/meta/test_ci_result_covers_every_job.py` (the
  gated/ungated partition: `plan` is neither; extend the test's classification rather than editing its logic)
- Test: `tests/meta/test_ci_plan_job.py` (new)

**Interfaces:**
- Consumes: Task 1's `vibey-gh ci-areas`.
- Produces: job `plan` (`name: CI plan`, ubuntu, `timeout-minutes: 10`, no `needs`) with outputs
  `areas` (JSON list), `full` (`'true'|'false'`), `tier` (`'pr'|'full'`), computed per event:
  `pull_request` base = `github.event.pull_request.base.sha`, head = `github.sha`'s merge ref parent as
  GitHub provides (use `github.event.pull_request.head.sha`); `push` base = `github.event.before`
  (all-zero before, i.e. a new branch, means `full`); `merge_group` base =
  `github.event.merge_group.base_sha`, head = `github.event.merge_group.head_sha`; `workflow_dispatch`
  and `schedule` mean `full`. Each value reaches the shell via `env:`.
  It writes the decision and its reasons to `$GITHUB_STEP_SUMMARY`. **It skips nothing in this task:**
  no other job reads its outputs yet.

- [ ] **Step 1: Write failing meta tests**: `plan` exists, has no `needs`, has the three outputs, has a
  `timeout-minutes` entry in the limits TOML, is in `ci-result.needs`; its checkout uses `fetch-depth: 0`
  or fetches the base commit (a shallow clone cannot diff: assert one of the two); no `${{` inside `run`;
  the steps compute the base per event as specified (assert each of the four event branches by
  executing the step's shell with sample `env:` and a stub `vibey-gh` on PATH that echoes its arguments:
  the test checks the `--base`/`--head` arguments it received for each event).
- [ ] **Step 2: Run and confirm failure.**
- [ ] **Step 3: Add the job.** Install only `vibey-gh` (not the whole workspace): `pip install` from the
  checkout's `src/vibey_tools/gh` with its own dependencies, as the `tools` row does; measure and report
  how long `plan` takes (target: under a minute).
- [ ] **Step 4: Validate with `actionlint` and the meta suite.** Open the PR; its own run is the first
  proof: the job summary must show the areas for this very PR (`ci`, `python` tests, `full` true because
  `ci.yml` changed). State the observed values in the PR description.
- [ ] **Step 5: Commit:** `git commit -m "ci: a plan job reports the changed areas and the tier, skipping nothing"`

---

### Task 3: Jobs consume the plan (this is the task that changes what runs)

**Files:**
- Modify: `.github/workflows/ci.yml` (job-level `if:` on area jobs; `fromJSON` matrices for `tools`,
  `postgres-compatibility`, `desktop`; the VS Code path)
- Create: `.github/ci-matrices.toml` (the PR-tier and full-tier rows, one source for both)
- Modify: `src/vibey_tools/gh/vibey_gh/ci_areas.py` (a `matrix` method) and its CLI
  (`vibey-gh ci-matrix --job <name> --tier <pr|full>` printing the JSON matrix), `test_ci_areas.py`
- Test: `tests/meta/test_ci_tiers_keep_every_row.py` (new)

**Interfaces:**
- Consumes: Task 2's outputs `areas`, `full`, `tier`; the existing matrix rows (listed in the parsed
  `ci.yml` at the base commit: `tools` 24 rows, `postgres-compatibility` [14..18], `desktop` 4 rows).
- Produces:
  - **PR tier rows** (when `tier == pr`): `tools`: every package at Python 3.12 only, ubuntu (8 rows), and
    only the packages whose area changed; `postgres-compatibility`: 14 and 18; `desktop`: ubuntu only.
  - **Full tier rows**: exactly today's rows (the meta test compares them to the committed full set).
  - Job-level `if:` per area: `krypton-app` (`krypton_app` or full), `vibey-core` and `app` (`vscode`/`app`
    or full), `desktop` (`desktop` or full), `image`, `chart`, `cluster-smoke` (`deploy`, `python` or full),
    `tools`/`tools-lint` (`tools`, `python` or full), `gates`/`noloss`/`postgres-compatibility` (`python` or
    full). A docs-only PR therefore skips all of them and runs `uv-lock`, `lint`, `plan`, `ci-result`.
    `lint` and `uv-lock` always run.
  - A `docs` strict build job is OUT of scope here (queued in the master plan as CI-E).

- [ ] **Step 1: Write the failing tests** `test_ci_tiers_keep_every_row.py`: (a) the union of PR-tier and
  full-tier rows for each matrix job equals the rows in `ci.yml` at the base commit (read it with
  `git show <merge-base>:.github/workflows/ci.yml`, or commit a snapshot `tests/meta/ci_matrix_snapshot.json`
  generated once and kept: choose the snapshot, and say why); (b) every PR-tier row is a member of the
  full tier (no row exists only in the PR tier); (c) each area job's `if:` references only `needs.plan.outputs`;
  (d) no job's `if:` references `needs.<other>.result` (skip must depend on the diff only; Global
  Constraints); (e) every job that gained an `if:` has `plan` in `needs`; (f) `plan` failing results in
  `full` for dependants: assert the `if:` expressions treat an empty/failed plan output as full
  (`needs.plan.outputs.full != 'false'`).
- [ ] **Step 2: Run and confirm failure.**
- [ ] **Step 3: Move the matrices** into `ci-matrices.toml` and generate each job's `matrix` with
  `fromJSON(needs.plan.outputs.<job>_matrix)`; extend `plan` to emit `tools_matrix`, `postgres_matrix`,
  `desktop_matrix` via `vibey-gh ci-matrix`. `strategy.fail-fast` stays `false`. Keep `name:` templates
  exactly as they are.
- [ ] **Step 4: The two required VS Code checks.** Their names are `VS Code extension (ubuntu-latest)` and
  `(macos-latest)`. Decide and implement ONE of these, justify it in the report, and pin it with a meta test:
  (A) the VS Code job is never skipped at job level: it always runs both rows, and the steps inside are
  gated by `if:` so a non-VS-Code PR passes in seconds under the same names; or
  (B) two fixed-name non-matrix jobs with those exact names, each skipped by `if:` (a skipped non-matrix job
  reports its fixed name as `skipped`). Prefer (B) only if the meta test proves the check names are
  byte-identical to the required ones. If neither can be shown to keep both names reporting, STOP and report.
- [ ] **Step 5: First-run proof.** In the PR description, record for FOUR synthetic diffs what the plan job
  produced and which jobs ran: a docs-only change, a `src/vibey/` change, a `clients/vscode/` change,
  and a `ci.yml` change. Produce them by pushing four throwaway draft PRs from this branch (do not merge
  them) or by running `vibey-gh ci-areas` locally against four constructed diffs and attaching the output:
  state which you did. Report the job count and the macOS job count of each.
- [ ] **Step 6: Commit:** `git commit -m "ci: skip unchanged areas and run the small matrix on pull requests"`

---

### Task 4 (OPERATOR-GATED, not started without a yes): the nightly full run

**Files:** `.github/workflows/ci-nightly.yml` (new) or a `schedule:` trigger on `ci.yml`.

**Why gated:** every scheduled workflow in this repository is currently `disabled_manually`, and the
reason for each is unknown (`docs/architecture/evidence/ci-workflow-state-*.md`). A new schedule makes a
runner-minute commitment every night and a failure needs an owner. Before writing it, ask the operator:
(a) whether scheduled workflows are meant to be disabled, (b) who owns a red nightly (the master plan says
it opens an issue through `vibey-gh issue_automation` and carries a skip-if-the-tip-is-unchanged guard
like `release-binaries.yml`'s plan step), (c) the hour. Until then the tiers in Task 3 give the full
matrix at `merge_group`, promotion and `push` to `main`, which is the minimum the operator-approved design
requires; the nightly adds same-day signal for develop pushes only.

---

## Not in this plan

- Sharding the root suite, native arm64 image, caches, SHA pinning, SBOM, `docs` strict build (CI-E, CI-H to
  CI-K of the master plan): later sub-plans, each editing `ci.yml` after this one lands.
- Changing any required check or ruleset. If Task 3 step 4 needs `.vibey-gh.toml` to change, stop and ask.
