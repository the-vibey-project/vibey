## Title
fix(gh): every link of review → merge train → promote is an explicit dispatch; workflow_run stays a backstop

## Why
CLAUDE.md, ADR-0028 and ADR-0036 say feature PRs squash into `develop` through the merge
train, and `vibey-gh promote` moves `develop` to `main`. On 2026-09-22 about 15:10Z, the last
**Merge train** run was 2026-09-21T19:21:38Z and the last **Promote** run 19:22:20Z. #317
(`62c75d77`, the evaluate/review split) merged at 19:29:03Z. Every **PR review** run since then
is a `workflow_dispatch` (`issue-audit/gaps.md` L1, lines 522-532). Nothing reaches `main`.

What the templates say at integration HEAD `d3b4a388`
(`src/vibey_tools/gh/vibey_gh/templates/workflows/`):
- `pr-evaluate.yml:356` and `:381` dispatch `pr-review.yml` with `github.token`. So since #317,
  PR review runs are started by `GITHUB_TOKEN`.
- `pr-review.yml`'s `gate` job already dispatches `merge-train.yml` explicitly when the gate
  succeeds. Its permissions are at `:1379-1382` (`actions: write`) and the call is at about
  `:1497-1500`. Its `workflow_run` trigger on "PR review" (`merge-train.yml:8-10`) is a second path.
- `merge-train.yml` has **no** dispatch of Promote. Promote is reached only by `workflow_run`
  on "Merge train" (`promote-to-main.yml:20-22`), a Monday cron (`:23-24`), or by hand.
  `merge-train.yml:25-28` grants only `actions: read`.

**Hypotheses, not facts.** Confirm or refute them with the evidence checklist below.
- H1: completing a run that `GITHUB_TOKEN` dispatched raises no `workflow_run` for other
  workflows. If H1 holds, the "PR review → Merge train" `workflow_run` path died with #317, and
  so would "Merge train → Promote" whenever the train was itself dispatched.
- H2: GitHub's limit of three `workflow_run` levels. #317 put one more level between CI and Promote.
- H3, independent of H1 and H2: no `PR review / gate` has succeeded since the paid key ran out of
  credit and the sovereign runners began failing to register (gaps.md L2), so the explicit
  review → train dispatch never fired either.

The fix holds under all three. Each link dispatches the next one explicitly. The GitHub docs
exempt `workflow_dispatch` from the `GITHUB_TOKEN` rule, and dispatch is not a `workflow_run`
level. `workflow_run` stays as a backstop, and a contract test keeps every link alive (12.c).

## Required behaviour
1. In the template `merge-train.yml`:
   - The workflow `permissions` block (`:25-28`) becomes `actions: write`, keeping
     `contents: write` and `pull-requests: write`.
   - After the step `Merge what is ready` (`:88-97`), a new last step:
     ```yaml
           - name: Hand develop to Promote
             if: ${{ inputs.dry_run != true }}
             env:
               GH_TOKEN: ${{ github.token }}
               REPO: ${{ github.repository }}
             run: |
               set -euo pipefail
               # An explicit dispatch, not only Promote's workflow_run trigger: a run started by
               # GITHUB_TOKEN may raise no workflow_run for other workflows, and workflow_run
               # chains stop at three levels. Promote re-reads develop and main itself, so a
               # dispatch with nothing to promote is a no-op (its own concurrency group
               # serializes it).
               gh workflow run promote-to-main.yml --repo "$REPO" \
                 --ref "${{ github.event.repository.default_branch }}"
     ```
   - Every other line is unchanged.
2. The two rendered copies are regenerated, never hand-edited: `.github/workflows/merge-train.yml`
   at the repository root, and `src/vibey_tools/gh/.github/workflows/merge-train.yml`. Run
   `uv run vibey-gh install` at the root and again in `src/vibey_tools/gh`. After that,
   `git diff --stat` must show only the template, the two rendered `merge-train.yml` files
   and the test file. Revert anything else `install` touched (hook files outside the tree are fine).
3. A contract test in `src/vibey_tools/gh/test/test_templates.py`, appended:
   `test_every_link_of_the_delivery_chain_is_an_explicit_dispatch`. It is parametrized over
   `[("pr-evaluate.yml", "pr-review.yml"), ("pr-review.yml", "merge-train.yml"), ("merge-train.yml", "promote-to-main.yml")]`.
   For each `(upstream, downstream)` it loads both templates with `yaml.safe_load` and asserts:
   - some step in some job of `upstream` has a `run` containing `gh workflow run {downstream}`;
   - that job, or the workflow, grants `actions: write`;
   - `downstream`'s `on` has a `workflow_dispatch` key. PyYAML loads `on` as `True`, so read
     `spec.get("on", spec.get(True))`.
   The failure message names the broken link.
4. A second appended test, `test_the_merge_train_hands_develop_to_promote_only_on_a_real_run`,
   asserts that the new step's `if` contains `inputs.dry_run != true`, and that it is the last
   step of the `merge` job.

## Where to change
- `src/vibey_tools/gh/vibey_gh/templates/workflows/merge-train.yml` (97 lines; use edit_file).
- The two rendered copies, regenerated by `vibey-gh install` as in point 2.
- `src/vibey_tools/gh/test/test_templates.py` (append only).

## Evidence checklist (reviewer or operator: not code; record the results in the PR description)
Run these with a `gh` authenticated for `the-vibey-project/vibey`:
1. `gh run list -R the-vibey-project/vibey --workflow "Merge train" --limit 15 --json databaseId,event,createdAt,conclusion`
   confirms the last run time and its event.
2. `gh run list -R the-vibey-project/vibey --workflow "PR review" --limit 40 --json databaseId,event,createdAt,conclusion`:
   are all runs since 2026-09-21T19:29Z `workflow_dispatch`?
3. For two of those runs:
   `gh api repos/the-vibey-project/vibey/actions/runs/<id> --jq '{event, actor: .actor.login, triggering_actor: .triggering_actor.login, conclusion, head_sha}'`.
   `triggering_actor == "github-actions[bot]"` is consistent with H1.
4. For the head of each run in step 3:
   `gh api repos/the-vibey-project/vibey/commits/<head_sha>/check-runs --jq '.check_runs[] | select(.name=="PR review / gate") | .conclusion'`.
   All `failure` means H3: the explicit dispatch never fired.
5. For the last Merge train run before 19:22Z:
   `gh api repos/the-vibey-project/vibey/actions/runs/<id> --jq '{event, workflow_run: .event}'`.
   Then walk the triggering runs back to CI and count the `workflow_run` levels (H2).
6. After this lane merges and one gate succeeds, a Promote run with
   `event == "workflow_dispatch"` follows the Merge train run. That is the fix's evidence.
   Record its run URL.

## Acceptance criteria
- [ ] The new contract test passes for all three links, and fails if either dispatch line is
      deleted: check by a scratch edit and revert.
- [ ] `test_repository_dogfoods_the_exact_rendered_workflows_and_hooks` (`test_templates.py:2476`) passes, so the rendered copies match.
- [ ] `test_the_merge_train_does_not_filter_on_the_triggering_runs_conclusion` (`:3048`) still passes.
- [ ] `test_every_rendered_run_block_is_valid_shell` (`:2940`) passes.
- [ ] vibey-gh's own gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_templates.py`:
- `test_every_link_of_the_delivery_chain_is_an_explicit_dispatch` (parametrized, 3 ids)
- `test_the_merge_train_hands_develop_to_promote_only_on_a_real_run`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider test/test_templates.py
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Restoring a review lane: `gap-ops-review-lane`, operator. Until a gate succeeds, nothing
  merges, which is correct.
- Removing the `workflow_run` triggers; they stay as backstops.
- The promote logic itself, and docs.

Commit as `fix(gh): each link of the delivery chain dispatches the next explicitly`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
