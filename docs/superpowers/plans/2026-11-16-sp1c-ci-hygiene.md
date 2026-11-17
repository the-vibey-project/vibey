# SP1-C CI Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every supply-chain and safety limit in CI a checked fact instead of a habit: every
action pinned by commit SHA, every base image and hook pinned by digest or SHA, every workflow
linted, every job time-limited, and a strict docs build on pull requests.

**Architecture:** One new `vibey-gh` command (`pin-actions`) does the toil of pinning. Four ratchet
censuses in `tests/meta/` (each a baseline in TOML that may only fall) then hold each rule so it
cannot regress. Two small `ci.yml` changes (a `docs` job and a workflow-lint gate) are the only
edits to the workflow, and this plan owns them.

**Tech Stack:** Python 3.12 (`vibey_gh`, argparse, pytest), GitHub Actions YAML, TOML ratchets.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md`, sections SP1 (tasks
CI-B leftovers, CI-C, CI-E), Global Constraints and Decisions. The measured state below was read on
develop `9e378a8e3` on 2026-11-16.

## What is already true (do not redo)

- `ci.yml`: 19 of 19 jobs have `timeout-minutes` (`tests/meta/ci_job_limits.toml`), top-level
  `permissions: {contents: read}`, a `lint` job, `ci-result`, a `plan` job, tiers and the nightly.
- Every workflow file has a top-level `permissions:`.
- 170 of 271 `uses:` lines are pinned by 40-hex SHA. The 101 that are not: `ci.yml` 50,
  `vibey-engine.yml` 10, `krypton-app.yml` 8, `minimum-specs.yml` 6, `review-canary.yml` 5, the
  rest in six other files. By action: `checkout@v4` 23, `upload-artifact@v4` 20,
  `download-artifact@v4` 15, `setup-python@v5` 14, `setup-uv@v7` 10, `setup-node@v7.1.0` 7,
  `pypa/gh-action-pypi-publish@release/v1` 4, `build-push-action@v7` 2, `setup-helm@v5` 2, and
  one each of `setup-uv@v3`, `setup-qemu-action@v4`, `setup-buildx-action@v4`,
  `medyagh/setup-minikube@latest`.
- 53 of 111 jobs outside `ci.yml` have no `timeout-minutes` (`pr-review.yml` 10 of 13,
  `vibey-engine.yml` 5 of 5, `krypton-app.yml` 4 of 4, `release-binaries.yml` 4 of 12,
  `release-surfaces.yml` 4 of 4, and 19 more across 19 files).
- Nothing in the repository runs actionlint or zizmor. `deploy/docker/Dockerfile` has two `FROM`
  lines and no digest on either. `.pre-commit-config.yaml` pins two hook repos by tag
  (`ruff-pre-commit v0.16.3`, `conventional-pre-commit v3.4.0`).
- Managed workflows (templates under `src/vibey_tools/gh/vibey_gh/templates/workflows/`) already
  pin by SHA and are protected from Dependabot by the `ignore:` list in `.github/dependabot.yml`.

## Global Constraints

- `ci.yml` has a single owner: every change to it is in this plan (Task 6, Task 4).
- A rendered workflow changes at its template under `src/vibey_tools/gh/vibey_gh/templates/workflows/`,
  never in `.github/workflows/`. Required checks change only through `.vibey-gh.toml` and its reconciler.
- Every structural rule gets a ratchet: a `tests/meta` census whose baseline is a TOML number that
  may only fall. Lowering a baseline is an ordinary commit; raising one fails the build.
- New and changed classes get an interface beside them (`vibey_gh/interfaces/<name>_interface.py`).
  A module-level function needs its reason written at the definition (ADR-0016).
- The gh tenant keeps its own 100% branch floor. Dogfood the family: any third-party tool
  (actionlint, zizmor) carries a written capability-gap reason at its use site.
- No `--no-verify`, no `--admin`. Conventional Commits. Commit trailer
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Work in `~/git/vibey-storm/sp1c-build` cut from `origin/develop`. After `uv run vibey-gh install`
  run `git config --worktree core.hooksPath .githooks`, then `uv run vibey-gh check`. Redirect hook
  output to a file; run `git commit` and `git push` in the foreground; push only when
  `sysctl -n vm.loadavg` is below 8.
- `src/vibey_tools/` is not in `[version] code_paths`, so tool changes do not cut a release.
  `pyproject.toml` is: do not edit the root `pyproject.toml` in this plan.

## Review Focus

1. `pin-actions` pins an annotated tag to the commit it points at, never to the tag object's own SHA.
2. `pin-actions` rewrites only `uses:` lines. A `uses:` that appears inside a `run:` script or a
   comment, a local `./` action and a `docker://...@sha256:` reference are left alone, and a
   reusable workflow (`owner/repo/.github/workflows/x.yml@ref`) is pinned like any action.
3. After the `docs` job exists, a PR touching no docs path skips it and `ci-result` stays green; a
   failing or cancelled `docs` job makes `ci-result` fail.
4. A new timeout never kills a job that legitimately runs longer than it: no limit sits within 50%
   of the job's observed maximum, and the macOS build jobs keep a limit above their p90.
5. A re-run of `pin-actions --apply` on an already-pinned tree changes nothing (idempotent), and
   `--check` needs no network.

---

### Task 1: `vibey-gh pin-actions` (the toil, automated)

**Files:**
- Create: `src/vibey_tools/gh/vibey_gh/pin_actions.py`,
  `src/vibey_tools/gh/vibey_gh/interfaces/pin_actions_interface.py`,
  `src/vibey_tools/gh/test/test_pin_actions.py`
- Modify: `src/vibey_tools/gh/vibey_gh/cli.py` (register `pin-actions` beside `ci-nightly`, near line 3090),
  `docs/reference/cli.md` (the command's entry, in the same table the other vibey-gh commands use)

**Interfaces:**
- Consumes: `GhTransportInterface` (`vibey_gh/interfaces/gh_transport_interface.py`); read
  `gh_transport.py` first for the method that issues a GET against the REST API.
- Produces:
  - `ActionUse` frozen dataclass: `path: Path`, `line: int`, `action: str` (e.g. `actions/checkout` or
    `owner/repo/.github/workflows/x.yml`), `ref: str`.
  - `PinActionsInterface` with `unpinned(text: str, path: Path) -> list[ActionUse]` (pure),
    `rewrite(text: str, shas: Mapping[tuple[str, str], str]) -> str` (pure),
    `resolve(action: str, ref: str) -> str` (network, returns a 40-hex commit SHA),
    `run(paths: Sequence[Path], *, apply: bool) -> int`.
  - CLI: `vibey-gh pin-actions [--apply] [PATH ...]`. Default paths: `.github/workflows/*.yml` and
    `.github/actions/*/action.yml`. Without `--apply` it never touches the network and exits 1,
    naming every unpinned use, when there is one; exit 0 when none.

- [ ] **Step 1: Write the failing tests** in `test_pin_actions.py`, with a fake transport that
  answers `GET /repos/{owner}/{repo}/commits/{ref}` from a dict:
  - `test_unpinned_finds_tag_branch_and_latest_refs` (`@v4`, `@release/v1`, `@latest`).
  - `test_unpinned_ignores_pinned_local_docker_and_non_uses_text` (a `run:` block and a `#` comment
    containing `uses: x@v1` yield nothing; Review Focus 2).
  - `test_a_reusable_workflow_reference_is_unpinned_like_an_action`.
  - `test_resolve_asks_the_commits_endpoint_so_an_annotated_tag_gives_its_commit` (Review Focus 1: the
    fake returns the commit SHA for the ref; assert the call path is `commits/<ref>`, not `git/ref/tags/`).
  - `test_rewrite_appends_the_ref_as_a_comment_and_keeps_an_existing_comment` (`uses: a/b@v4` becomes
    `uses: a/b@<40hex> # v4`; an existing trailing comment survives after it).
  - `test_rewrite_is_idempotent` and `test_check_mode_makes_no_network_call_and_exits_1`
    (Review Focus 5).
  - `test_a_ref_that_does_not_resolve_fails_loudly_and_leaves_the_file_unchanged`.
- [ ] **Step 2: Run** `cd src/vibey_tools/gh && python -m pytest -q test/test_pin_actions.py`; expected: FAIL (module missing).
- [ ] **Step 3: Implement** `PinActions(PinActionsInterface)` in `pin_actions.py` with a regex over
  `^\s*-?\s*uses:\s*(\S+)` lines only (parse line by line; never a YAML round-trip, which would
  reformat the file). Group refs per `(action, ref)` so each is resolved once. Every method
  is a method of the class; `declare` and `dispatch` follow `ci_nightly.py`.
- [ ] **Step 4: Run** the tests and the tenant's full suite
  (`python -m pytest -q`, 100% branch floor) and `python -m mypy vibey_gh`, `python -m black --check vibey_gh test`,
  `isort --check-only vibey_gh test`; expected: PASS.
- [ ] **Step 5: Commit** `feat(gh): vibey-gh pin-actions pins every uses: to a commit SHA`.

---

### Task 2: Pin every action in the repository, behind a ratchet

**Files:**
- Create: `tests/meta/test_actions_are_pinned_by_sha.py`, `tests/meta/unpinned_actions.toml`
- Modify: every file `vibey-gh pin-actions` reports (the hand-written workflows, 101 uses)

**Interfaces:**
- Consumes: Task 1's CLI.
- Produces: `tests/meta/unpinned_actions.toml` with `ceiling = <int>`, read by the census.

- [ ] **Step 1: Write the census** `test_actions_are_pinned_by_sha.py`: it walks `.github/workflows/*.yml`
  and `.github/actions/*/action.yml`, counts `uses:` lines that are not a 40-hex SHA, not `./`, not a
  `docker://` digest; asserts `count <= ceiling` and, when `count < ceiling`, fails with
  "lower the ceiling to N" (a ratchet that only falls). Test names:
  `test_the_unpinned_count_never_exceeds_the_ceiling`, `test_the_ceiling_is_exactly_the_count`,
  `test_a_synthetic_unpinned_use_is_counted`. Set `ceiling = 101`.
- [ ] **Step 2: Run** `uv run pytest -q tests/meta/test_actions_are_pinned_by_sha.py`; expected: PASS at 101.
- [ ] **Step 3: Apply.** With network, from the worktree: `uv run vibey-gh pin-actions --apply`, then
  `git diff --stat`. Review the diff for the four trap cases: the four
  `pypa/gh-action-pypi-publish@release/v1` lines (a branch ref; the comment must read `# release/v1`),
  `medyagh/setup-minikube@latest`, `astral-sh/setup-uv@v3` (the odd one out; keep its version, do
  not upgrade) and `actions/setup-node@v7.1.0`.
- [ ] **Step 4: Lower the ceiling to 0** in `unpinned_actions.toml` (the census then asserts zero).
  Run `uv run vibey-gh check` (managed workflows must still match their templates; the apply must
  not have touched a rendered file), then `uv run pytest -q tests/meta`.
- [ ] **Step 5: Commit** in two commits: `test(ci): ratchet unpinned actions at 101` and
  `fix(ci): pin every action by commit SHA`.

Note for the operator: Dependabot's `github-actions` ecosystem keeps bumping SHA-pinned hand-written
actions and updates the trailing version comment; the managed ones stay on the existing `ignore:` list.

---

### Task 3: Pin the container bases and the hook repos

**Files:**
- Modify: `deploy/docker/Dockerfile` (lines 30 and 155), `.pre-commit-config.yaml` (the two `rev:` lines),
  `.github/dependabot.yml` (add a `docker` ecosystem for `/deploy/docker`)
- Create: `tests/meta/test_bases_and_hooks_are_pinned.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: nothing later tasks use.

- [ ] **Step 1: Write the failing test** `test_bases_and_hooks_are_pinned.py` with
  `test_every_dockerfile_from_names_a_sha256_digest` (every `FROM <image>` carries `@sha256:<64 hex>`;
  a `FROM <stage>` that names an earlier `AS` stage is exempt) and
  `test_every_precommit_repo_rev_is_a_40_hex_sha` (a `local` repo has no `rev` and is exempt).
- [ ] **Step 2: Run it**; expected: FAIL naming both `FROM` lines and both hook repos.
- [ ] **Step 3: Resolve the digests.** The multi-arch index digest, so amd64 and arm64 both pull:
  `docker buildx imagetools inspect <image:tag> --format '{{.Manifest.Digest}}'` for
  `ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim` and `python:3.12-slim-bookworm`. Write them as
  `image:tag@sha256:...` (keep the tag; it is the human-readable half). For the hooks resolve each tag to its
  commit with `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha` and write `rev: <sha>  # <tag>`.
  If `docker buildx` is unavailable, `gh api` against the registry's manifest endpoint is the fallback.
- [ ] **Step 4: Run the test**; expected: PASS. Run `uv run pytest -q tests/meta/test_container_context.py
  tests/meta/test_ci_tiers_keep_every_row.py`, the two that read the Dockerfile.
- [ ] **Step 5: Commit** `fix(ci): pin container bases by digest and hook repos by SHA`.

---

### Task 4: actionlint and zizmor in the `lint` job, behind a ratchet

**Files:**
- Create: `scripts/workflow_lint.py` (a class `WorkflowLint` with `scripts/interfaces/workflow_lint_interface.py`
  beside it, following how `scripts/static_gates.py` is built), `tests/meta/workflow_lint_baseline.toml`,
  `tests/meta/test_workflow_lint_runner.py`
- Modify: `src/vibey_tools/gh/pyproject.toml` (the `dev` extra), `uv.lock`, `.github/workflows/ci.yml`
  (`lint` job: one step)

**Interfaces:**
- Consumes: the layout of `scripts/ci_cost_baseline.py` and `scripts/interfaces/ci_cost_baseline_interface.py`
  (the class-plus-interface shape and the `scripts.interfaces.x` import path the `scripts` static gate expects).
  The new script falls under the existing `scripts` row of `[[tool.vibey.static_gates]]` automatically, so
  the root `pyproject.toml` is NOT edited (it is in `code_paths`).
- Produces: `WorkflowLint.run() -> int`, exit 0 when each tool's finding count is at or below its baseline.

- [ ] **Step 1: Confirm the tools are installable and locked.** Add `zizmor` and `actionlint-py` to the gh
  tenant's `dev` extra (NOT the root `pyproject.toml`: it is in `code_paths`), run `uv lock`, and check
  `uv export --frozen --package vibey-gh --extra dev --no-emit-workspace | grep -i -E "zizmor|actionlint"`
  shows both with hashes and wheels for Linux x86-64 and macOS arm64. If either has no wheel for a
  platform in the CI matrix, stop and report: do not fall back to an unlocked download.
- [ ] **Step 2: Measure the baseline.** Run both tools over `.github/workflows` and `.github/actions`.
  Record the counts in `workflow_lint_baseline.toml` (`actionlint = N`, `zizmor = N`) with the tool
  versions and the date beside them. The master plan does not know these numbers; do not guess them.
- [ ] **Step 3: Write the failing tests** in `test_workflow_lint_runner.py`:
  `test_a_count_at_the_baseline_passes`, `test_a_count_above_the_baseline_fails_and_names_the_tool`,
  `test_a_count_below_the_baseline_fails_telling_you_to_lower_it` (ratchet), and
  `test_a_tool_that_exits_with_an_error_instead_of_findings_fails` (a crash is never a clean pass).
  Use a fake process runner passed to the class constructor.
- [ ] **Step 4: Implement** `WorkflowLint` (zizmor is run with its JSON output so the count is a count of
  findings, not of lines). Write the capability-gap reason at the class: the family has no workflow
  linter, and a misreading of the Actions expression grammar is exactly the failure that is expensive to
  find in CI.
- [ ] **Step 5: Wire it** as one step in the `lint` job, installing the two tools from the lock
  (`uv export --frozen --package vibey-gh --extra dev --no-emit-workspace | uv pip install --require-hashes -r -`)
  and running `python scripts/workflow_lint.py`. The pre-push hook is not changed here: it runs the
  gates the repository declares, and `ci.yml`'s `lint` job is the enforcement point.
- [ ] **Step 6: Verify** `uv run python scripts/workflow_lint.py` exits 0, `uv lock --check` passes, and the
  workflow edit passes the tool it just added. **Commit** `feat(ci): lint workflows with actionlint and zizmor, ratcheted`.

---

### Task 5: A time limit for every job in the hand-written workflows

**Files:**
- Create: `tests/meta/test_every_workflow_job_has_a_timeout.py`, `tests/meta/workflow_job_limits.toml`
- Modify: `.github/workflows/vibey-engine.yml`, `krypton-app.yml`, `minimum-specs.yml`,
  `release-binaries.yml`, `review-canary.yml`, `autonomy-scorecard.yml`, `backlog-cleanup.yml`,
  `delivery-estimate.yml`, `documentation-deep-scan.yml`, `openvsx.yml` (only the jobs the census names)

**Interfaces:**
- Consumes: `tests/meta/ci_job_limits.toml` (its rule and its `basis` vocabulary: `measured`,
  `unmeasured`, `kept`).
- Produces: `workflow_job_limits.toml` with `default_timeout_minutes`, `ceiling` (the count of jobs without
  a limit), and `[jobs."<file>.<job>"]` entries `{timeout_minutes, basis}`.

- [ ] **Step 1: Measure.** `scripts/ci_cost_baseline.py` reports wall time per workflow, not per job, so it
  cannot set a job limit (promoting it to a command is CI-L, not here). Measure per job the way
  `ci_job_limits.toml`'s header describes: read-only `gh api` GETs of each workflow's recent completed runs
  and their jobs, duration = `completed_at - started_at`, queue wait excluded, the slowest matrix cell's p90
  and maximum. Write the method, the window and the sample size `n` into the TOML header beside the numbers.
  Where a job has no history (a schedule that rarely runs), set `basis = "unmeasured"` and use 30. Apply the
  rule: `roundup5(max(2 x p90, 10))`, never within 50% of the observed maximum (Review Focus 4).
- [ ] **Step 2: Write the census.** Tests: `test_every_job_without_a_limit_is_counted_against_the_ceiling`,
  `test_the_ceiling_is_exactly_the_count`, `test_a_listed_limit_must_match_the_workflow`,
  `test_a_reusable_workflow_call_job_is_exempt` (a job with `uses:` takes no `timeout-minutes`).
  Set `ceiling = 53` first; the managed (templated) files are counted but cannot be fixed here (Task 6).
- [ ] **Step 3: Run**; expected: PASS at 53. **Step 4: Add the limits** to the hand-written files and
  entries to `workflow_job_limits.toml`; lower `ceiling` to the number Task 6 still owns, and run
  `uv run vibey-gh check` (the hand-written files are not rendered, so it must stay clean).
- [ ] **Step 5: Commit** `test(ci): ratchet jobs without a time limit at 53` then
  `fix(ci): a time limit on every hand-written workflow job`.

---

### Task 6: The same limit in the managed workflow templates

**Files:**
- Modify: the templates under `src/vibey_tools/gh/vibey_gh/templates/workflows/` that Task 5's census still
  names (`pr-review`, `pr-evaluate`, `release-surfaces`, `github-release`, `merge-train`,
  `promote-to-main`, `provenance`, `repository-profile`, `ruleset-drift`, `skip-markers`,
  `automation-bootstrap`, `branch-health`, `changelog`, `conventional-commits`), and the rendered files
  they produce, by running the renderer
- Modify: `tests/meta/workflow_job_limits.toml` (`ceiling` down to 0, entries for these jobs)

**Interfaces:**
- Consumes: Task 5's census and limits file.
- Produces: a `ceiling` of 0.

- [ ] **Step 1: Find the render command.** `uv run vibey-gh check --apply` (or `vibey-gh install`, whichever
  `vibey-gh check` itself prints on drift) re-renders the managed files from the templates. Edit a template,
  run it, confirm only the expected rendered file changed.
- [ ] **Step 2: Add `timeout-minutes` to every template job** using Task 5's method and rule, one entry per
  job. `pr-review.yml` calls a model: its limit comes from the measured p90 of its review jobs, not a guess.
- [ ] **Step 3: Verify.** `uv run vibey-gh check` is clean; the gh tenant's `tools-lint` drift check (both
  rendered copies, vibey-gh's own and the repository root's) passes:
  `(cd src/vibey_tools/gh && python -m pytest -q)`; `uv run pytest -q tests/meta`. Lower `ceiling` to 0.
- [ ] **Step 4: Commit** `fix(gh): a time limit on every managed workflow job`.

---

### Task 7: A strict docs build on pull requests

**Files:**
- Create: `docs/requirements.txt` (the release build already looks for exactly this path)
- Modify: `.github/workflows/ci.yml` (a `docs` job and its entry in `ci-result.needs`),
  `.github/ci-areas.toml` (`[jobs]` entry mapping `docs` to the `docs` area),
  `tests/meta/ci_job_limits.toml` (a `docs` entry), the CI-tiers snapshot test files if they enumerate jobs

**Interfaces:**
- Consumes: the `docs` area already in `ci-areas.toml`; the job-guard shape the other area jobs use
  (`!cancelled() && needs.uv-lock.result == 'success' && needs.lint.result == 'success' && (full != 'false' || area)`).
- Produces: a job named `docs`.

- [ ] **Step 1: Run the build locally first.** Install the three pins `release-surfaces.yml` uses
  (`properdocs==1.6.7`, `properdocs-theme-mkdocs==1.6.7`, `pymdown-extensions==12.0`) into a throwaway venv
  under `$TMPDIR` and run `properdocs build --strict` from the repository root. Record the result. If it
  fails on tracked content, that is the defect this job exists to catch: fix the content in this task only if
  it is a handful of broken links; otherwise stop and report the count.
- [ ] **Step 2: Write the failing tests.** The existing meta tests will fail until the job is consistent:
  `test_ci_plan_job.py` (job is mapped in `[jobs]`), `test_ci_job_hygiene.py` (needs a limit entry),
  and the `ci-result` needs test. Run them to see each name the missing piece.
- [ ] **Step 3: Write `docs/requirements.txt`** with the three exact pins, then add the `docs` job: checkout,
  `setup-python` 3.12 (use the SHA pins from Task 2), `pip install -r docs/requirements.txt`,
  `properdocs build --strict`. Limit: the measured build time from Step 1, rounded by the rule in Task 5.
- [ ] **Step 4: Prove both Review Focus 3 cases.** Push a throwaway PR that touches one docs file with a
  broken link and confirm `docs` fails and `CI result` fails; push one that touches only `src/` and confirm
  `docs` is skipped and `CI result` is green. Record both run URLs in the PR description. Close the probes.
- [ ] **Step 5: Commit** `feat(ci): a strict docs build on pull requests that touch docs`.

---

### Decision (2026-11-17): how the pins stay fresh

The final review found that Dependabot's `ignore:` list, which protects the managed workflow
templates, also stops it bumping the five actions in the hand-written workflows, and that
`pin-actions` only pinned refs that were not yet pinned. Options weighed: (a) narrow the ignore
list (impossible: Dependabot ignores a dependency, not a file); (b) a scheduled workflow that
runs `--refresh` and opens the pull request itself; (c) `--refresh` by hand plus a weekly check
that opens one tracking issue. Chosen: (c), with `--refresh` and `--check-stale` in the tool.
Moving a pin changes what runs in the pipeline, so a person reads that diff; (b) needs a token
whose pull requests trigger CI and writes workflow files, a larger grant than an issue needs.
The check is the 12.e half: it says out loud when a pin is stale or cannot be checked. Held
actions and issue labels are configuration (`[pin_actions]` in `.vibey-gh.toml`), not code.
Revisit (b) if the issues are acted on without ever being questioned.

## Not in this plan

- **CI-D locked tenant installs** (`uv export --frozen` with hashes, nightly latest-dependency canary,
  lowest-direct run at promotion): SP1-D. It changes how every tenant row installs, so it gets its own plan.
  `uv export --frozen --offline --package vibey-gh --extra dev --no-emit-workspace` was checked on
  2026-11-16 and works offline with hashes.
- **CI-G, CI-H, CI-I, CI-J, CI-K, CI-L** (one promotion run per attempt; shard the root suite; image built
  once; caches; de-duplication; re-measure): SP1-E to SP1-G, in that order.
- Making `ci-result` the one required check and removing the develop admin bypass shipped as #1911 (merged);
  nothing in this plan touches rulesets.
- Promoting `scripts/ci_cost_baseline.py` to `vibey-gh ci-cost` (its docstring assigns that to CI-L).

## Self-review

- **Spec coverage:** CI-B leftovers (actionlint, zizmor) are Task 4; CI-C is Tasks 2, 3, 5, 6; CI-E is
  Task 7; the SHA-pin tooling (toil, 12.e) is Task 1. CI-D onward is deferred by name above.
- **Type consistency:** `ActionUse`, `PinActionsInterface.{unpinned,rewrite,resolve,run}` and the
  `unpinned_actions.toml`, `workflow_job_limits.toml` and `workflow_lint_baseline.toml` names are used
  identically wherever they recur.
- **Numbers are measured, not assumed:** 271/170/101 and 111/53 were read from the tree on 2026-11-16;
  the actionlint and zizmor baselines are deliberately a step (Task 4 Step 2) because they are not known yet.
