## Title
ops: yank every release superseded by the ratifications of 2026-09-22 (#392, #325, #384, #385)

## Why
Constitution V.4 (`src/vibey_tools/gh/docs/constitution.md:140-148`) says a ratified change to
the canon "immediately yanks all previous versions … on every index … where an index offers no
yank API the demand falls to the maintainer as their immediate next act". #325, #384, #385 and
#392 ratified canon changes on 2026-09-22. No yank has happened and nothing tracks it
(`issue-audit/gaps.md` L9). PyPI and TestPyPI offer no yank API
(`src/vibey_tools/gh/vibey_gh/yank.py:4-26`), so this is the maintainer's task.

Implementer: the operator. The storm runner skips `gap-ops-*` lanes.

## Required behaviour
Every release the ratifications supersede is yanked on every index, or the operator records a
decision to sequence it (see item 3). The evidence is recorded.

## Where to change
Nothing in the tree.

## Operator checklist (human — not code; the storm runner must skip gap-ops-* lanes)
1. [ ] Find each ratifying merge's parent: `git log --oneline --merges -- src/vibey_tools/gh/docs/doctrines.md src/vibey_tools/gh/docs/constitution.md | head`.
   Record the SHA before the first 2026-09-22 ratification as `BEFORE`.
2. [ ] List what is superseded:
   - `uvx --from vibey vibey-gh report-superseded --index pypi --project vibey --version <newest vibey on PyPI> --governance-since <BEFORE>`;
   - the same for `--index testpypi --project vibey-dev`.

   `--version` is excluded from the list by identity, so name the newest release there.
3. [ ] **Decide the sequencing and record it.** If every published `vibey` release is yanked
   before 3.0.0 exists, `pip install vibey` with no pin selects a yanked release, with a warning
   (PEP 592). V.4 says "immediately". Choose one:
   - (a) yank now;
   - (b) yank the moment 3.0.0 is published, recording why the hours between were accepted.

   Write the choice in this issue.
4. [ ] Yank each listed version at https://pypi.org/manage/project/vibey/releases/ (Options,
   Yank; give the reason "superseded by the ratification of #392 (Constitution V.4)"). Do the
   same at https://test.pypi.org/manage/project/vibey-dev/releases/.
5. [ ] **The retired distribution names** (`claudeloop`, `codexloop`, `cursorloop`,
   `agyloop`, `opencodeloop`, `qwenloop`, `vibey-gh`, `vibey-skills`, `vibey-bootstrap`,
   `vibey-runners-common`, if published). V.4 says "every prior release on every index". Rule
   whether their releases count as prior versions of this code, and if so yank them too, recording the decision.
6. [ ] Record the evidence: rerun step 2. The list must now be empty, because yanked releases
   are not reported (`yank.py`, `released_versions`). Paste the output here.
7. [ ] Append `gap-ops-yank-392` to `STORM/integrated.txt`.

## Acceptance criteria
- [ ] Step 6's rerun prints no superseded release on either index, or the recorded sequencing
      decision in step 3 says when it will.
- [ ] The decisions in steps 3 and 5 are recorded in this issue.

## Tests to write first (TDD)
None. This is a human checklist.

## Checks the lane must run (all must pass)
None in code.

## Out of scope
- The automation for future ratifications (`gap-release-yank-workflow-1`, `-2`).

Commit nothing. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
