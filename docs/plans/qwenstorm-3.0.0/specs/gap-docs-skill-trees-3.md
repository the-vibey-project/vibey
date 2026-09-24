## Title
docs(skills): the vibey-releasing skill teaches the Article V.4 yank workflow and how a breaking release is written up

## Why
The `vibey-releasing` skill (`.claude/skills/vibey-releasing/SKILL.md`) predates two changes
(`issue-audit/gaps.md` M3, lines 639-642):
- `:187-189` says a ratified canon change requires every prior release to be yanked
  (Article V.4, `src/vibey_tools/gh/docs/constitution.md`) but names no mechanism. After
  `gap-release-yank-workflow-2`, `.github/workflows/release.yml` runs
  `vibey-gh report-superseded … --governance-since … --checklist-out yank.md` after every
  publish (jobs `superseded-testpypi` and `superseded-pypi`) and, for a range that carries a
  governance change, opens an issue labelled `article-v4-yank` with the checklist
  (`STORM/specs/gap-release-yank-workflow-2.md:13-38`).
- `:191-198` ("The changelog") says only that `[Unreleased]` entries move under
  `## [x.y.z] (date)`. `gap-docs-changelog` wrote 3.0.0 as `## [3.0.0] (unreleased)` with
  every breaking commit and a data-loss warning first; the skill should teach that shape.
The same text lives in `.agents/skills/vibey-releasing/SKILL.md`,
`.cursor/rules/vibey-releasing.mdc` and `.agent/rules/vibey-releasing.md`.

## Required behaviour
1. Confirm: `grep -n "superseded-testpypi\|superseded-pypi\|article-v4-yank\|--checklist-out" .github/workflows/release.yml`
   prints all four names. If any is missing, STOP and report BLOCKED.
2. Write `.qwenstorm/skill_edit.py` and run it: for each of the four files, apply both pairs
   with `assert text.count(old) == 1`, then write the file.
   - V4. `old` (three lines, copied from `:187-189`):
     ```
     A ratified change to the doctrine canon is also a release event: Article V.4 of
     the constitution (`src/vibey_tools/gh/docs/constitution.md`) requires every prior
     release to be yanked. See the `vibey-architecture` skill.
     ```
     `new`:
     ```
     A ratified change to the doctrine canon is also a release event: Article V.4 of
     the constitution (`src/vibey_tools/gh/docs/constitution.md`) requires every prior
     release to be yanked. After each publish, `release.yml`'s `superseded-testpypi`
     (on `develop`) and `superseded-pypi` (on `main`) jobs run
     `vibey-gh report-superseded --governance-since <the previous head> --checklist-out yank.md`.
     When the published range carries a governance change, they open an issue labelled
     `article-v4-yank` whose body is the checklist of releases to yank; the maintainer
     yanks them on the index and ticks the list. An ordinary release only logs its
     retention housekeeping. See the `vibey-architecture` skill.
     ```
   - CL. `old` (one line, from `:196`):
     ```
     When a version ships, the `[Unreleased]` entries move under `## [x.y.z] (date)`.
     ```
     `new`:
     ```
     When a version ships, the `[Unreleased]` entries move under `## [x.y.z] (date)`.
     A release written up before its date is known sits directly under `[Unreleased]`
     as `## [x.y.z] (unreleased)`, and its release commit replaces `(unreleased)` with the
     date (3.0.0 was written this way). A major release lists every breaking commit — a
     `!` subject or a `BREAKING CHANGE:` footer since the previous release — with the
     footer's text, and leads with anything that can lose data on upgrade.
     ```

## Where to change
- `.claude/skills/vibey-releasing/SKILL.md`, `.agents/skills/vibey-releasing/SKILL.md`,
  `.cursor/rules/vibey-releasing.mdc`, `.agent/rules/vibey-releasing.md`, by the script only.

## Acceptance criteria
- [ ] The script edits all four files; every assertion holds.
- [ ] `grep -c "article-v4-yank"` and `grep -c "(unreleased)"` print at least 1 in each of the four files.
- [ ] `git diff` changes no header line and no SD-01 line.
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes.

## Tests to write first (TDD)
None new: the tree-parity and SD-01 carriage meta-tests hold the four trees.

## Checks the lane must run (all must pass)
    grep -n "superseded-testpypi\|superseded-pypi\|article-v4-yank\|--checklist-out" .github/workflows/release.yml
    python3 .qwenstorm/skill_edit.py
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    git diff --stat

## Out of scope
- `release.yml` and vibey-gh (`gap-release-yank-workflow-*`); yanking anything (`gap-ops-yank-392`).
- Other skills; CHANGELOG.md.

Commit as `docs(skills): the vibey-releasing skill teaches the Article V.4 yank workflow and the breaking-release write-up`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
