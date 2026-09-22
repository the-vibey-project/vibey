## Title
ci(release): every publish reports superseded releases, and a ratifying range opens the maintainer's yank checklist

## Why
Constitution V.4 (`src/vibey_tools/gh/docs/constitution.md:140-148`) makes the yank the
maintainer's "immediate next act" after a ratifying merge. `report-superseded` appears in no
workflow (`issue-audit/gaps.md` L9, lines 596-606). The publish jobs are in `.github/workflows/release.yml`:
- `testpypi` (`:99-113`) publishes `vibey-dev` on `develop`;
- `pypi` (`:165-178`) publishes `vibey` on `main`.

`release.yml` is repository-local; vibey-gh does not render it (`src/vibey_tools/gh/README.md:974`).
`gap-release-yank-workflow-1` added `--checklist-out`.

## Required behaviour
1. `release.yml` gains two jobs. Each one:
   - checks out with `fetch-depth: 0`;
   - installs the tree's own vibey-gh the way `realign` does (`:180-250`, the "Install the tree's own vibey-gh" step);
   - has `permissions: { contents: read, issues: write }`.

   Job `superseded-testpypi`: `needs: [build, testpypi]`, `if: github.ref == 'refs/heads/develop'`.
   It runs
   `vibey-gh report-superseded --index testpypi --project vibey-dev --version "${VERSION}" --governance-since "${BEFORE}" --checklist-out yank.md`,
   with `VERSION: ${{ needs.build.outputs.version }}` and `BEFORE: ${{ github.event.before }}`.

   Job `superseded-pypi`: `needs: [build, pypi]`, `if: github.ref == 'refs/heads/main'`, and
   the same command with `--index pypi --project vibey`.
2. In both jobs, a final step opens the issue only for a governance range:
   ```bash
   set -euo pipefail
   if [ -s yank.md ] && grep -q 'Article V.4' yank.md; then
     gh label create article-v4-yank --color B60205 --description "Constitution V.4: yank superseded releases" --force
     gh issue create --title "Article V.4: yank every release superseded by ${VERSION} on ${INDEX_LABEL}" \
       --body-file yank.md --label article-v4-yank
   fi
   ```
   The environment is `GH_TOKEN: ${{ github.token }}`, with `INDEX_LABEL` set to `TestPyPI` or
   `PyPI`. Retention housekeeping, a non-governance list, stays in the job log only, so ordinary
   releases do not open an issue each time.
3. A new meta-test, `tests/meta/test_release_reports_superseded.py`, loads `release.yml` with
   `yaml.safe_load` and asserts:
   - both jobs exist;
   - each `needs` its publish job and has the matching `if`;
   - each runs `report-superseded` with `--governance-since` and `--checklist-out`;
   - each has `issues: write`;
   - the issue step is gated on `Article V.4`.
   Its failure message names Constitution V.4.

## Where to change
- `.github/workflows/release.yml` (edit_file).
- New `tests/meta/test_release_reports_superseded.py`, with the provenance header.

## Acceptance criteria
- [ ] The meta-test passes, and fails if either job's `--governance-since` is removed (check by a scratch edit and revert).
- [ ] `test_every_rendered_run_block_is_valid_shell` has no counterpart here, so run
      `bash -n` on each new `run` block, extracted with a short Python snippet in the test.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes.

## Tests to write first (TDD)
`tests/meta/test_release_reports_superseded.py`:
- `test_each_publish_is_followed_by_a_superseded_report`
- `test_a_ratifying_range_opens_the_yank_checklist_issue`
- `test_the_new_run_blocks_are_valid_bash`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Yanking. PyPI has no API, so the maintainer does it (`gap-ops-yank-392` for the current debt).
- Other indexes: the packaging channels (`gap-pkg-*`) join later through `gap-gh-release-channels`.
- Docs.

Commit as `ci(release): report superseded releases and open the Article V.4 checklist`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
