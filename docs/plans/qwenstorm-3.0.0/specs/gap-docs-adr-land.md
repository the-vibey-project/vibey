## Title
docs(adr): land ADR-0045, 0046, 0047, the installer ADR (0048) and the ORM ADR (0049)

## Why
Five decision records exist only as storm drafts (`issue-audit/gaps.md` M7, lines 671-682):
- `STORM/specs/ADR-test-harness-queue.md` (0045), with its amendment
  `STORM/specs/ADR-test-harness-fakes-amendment.md`, which says it is appended below the draft;
- `STORM/specs/ADR-two-loops.md` (0046);
- `STORM/specs/ADR-surface-lanes.md` (0047);
- `STORM/specs/ADR-installer.md` (numbered `NNNN`, the next free number: 0048);
- `STORM/specs/ADR-orm.md` (numbered `NNNN`, the next free number after it: 0049).

At integration HEAD `4317cff6` the last record is
`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md`. An ADR that is not in
the nav, or a count that disagrees with the files on disk, fails
`tests/meta/test_adr_counts.py:31-53`. The count is written in five places: `CLAUDE.md:221`,
`AGENTS.md:237`, `GEMINI.md:165` (which also writes the range `0001–0044`), `README.md:312` and
`docs/index.md:299`. ADR-0044 was landed the same way; its landed copy dropped the local
checkout path the draft named (compare `specs/ADR-rabbitmq-queue.md:3` with the landed `:3`).

`STORM` below means `/private/tmp/claude-501/storm/qwenstorm-3.0.0`. The lane copies the drafts
as they are at run time; it does not rewrite them. Status lines stay as the drafts write them
(`proposed`): `gap-docs-adr-status-2` sets them against the canon.

## Required behaviour
1. Before anything else, run `ls docs/architecture/decisions | tail -1`. It must print
   `0044-job-queue-port-and-loop-services.md`. If it prints anything else, another ADR landed
   first: STOP and report BLOCKED with that output.
2. Create exactly these five files (use the `shell` tool with `bash -c`; do not retype them):
   - `docs/architecture/decisions/0045-the-test-harness-runs-once-fed-by-a-queue.md`:
     ```
     { cat STORM/specs/ADR-test-harness-queue.md; printf '\n## Amendment — every seam has an in-memory fake, and the default run needs nothing outside the process\n\n'; tail -n +6 STORM/specs/ADR-test-harness-fakes-amendment.md | sed 's/^## A\([0-9]\)/### A\1/'; } > docs/architecture/decisions/0045-the-test-harness-runs-once-fed-by-a-queue.md
     ```
     (Line 6 of the amendment is its `**Status:**` line; lines 1-5 are its title and the
     instruction to append it, which are dropped.)
   - `0046-two-loops-sovereignloop-and-paidloop.md`: `cp STORM/specs/ADR-two-loops.md …`.
   - `0047-every-sovereign-surface-runs-in-one-lane.md`: `cp STORM/specs/ADR-surface-lanes.md …`.
   - `0048-vibey-install-installs-the-local-stack.md`: `cp STORM/specs/ADR-installer.md …`, then
     change line 1's `# NNNN —` to `# 0048 —`.
   - `0049-persistence-goes-through-the-orm.md`: `cp STORM/specs/ADR-orm.md …`, then change
     line 1's `# NNNN —` to `# 0049 —`.
   Write `STORM` out as the absolute path.
3. Remove the local checkout paths from the headers with checked replacements (EDITING-RULES
   rule 2; each `old` must occur exactly once, else STOP and report which one):
   - in 0045: ``unless it names a storm file (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/…`), which is read at the same time``
     becomes `unless it names a QwenStorm 3.0.0 specification, which is read at the same time`;
   - in 0046: ``the storm integration tree `/private/tmp/claude-501/storm/qwenstorm-3.0.0/integration` at `391673c2` ``
     (no trailing space) becomes ``the storm integration branch (`storm/integration`) at `391673c2` ``;
   - in 0047: ``unless it names a storm file (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/…`)``
     becomes `unless it names a QwenStorm 3.0.0 specification`.
   Afterwards `grep -c /private/tmp docs/architecture/decisions/004[5-9]-*.md` prints 0 for each.
4. `properdocs.yml`: after line 100 (the `0044 — …` nav entry), add five entries in the same
   form, in order:
   ```
             - "0045 — The test harness runs once per machine and takes its runs from a queue": architecture/decisions/0045-the-test-harness-runs-once-fed-by-a-queue.md
             - "0046 — Two loops, sovereignloop and paidloop, rotated in two layers on queues": architecture/decisions/0046-two-loops-sovereignloop-and-paidloop.md
             - "0047 — Every sovereign surface runs in one lane fed by RabbitMQ": architecture/decisions/0047-every-sovereign-surface-runs-in-one-lane.md
             - "0048 — `vibey install` installs everything a developer needs on the two default OSes": architecture/decisions/0048-vibey-install-installs-the-local-stack.md
             - "0049 — Every persistence access goes through the ORM, behind a declared interface": architecture/decisions/0049-persistence-goes-through-the-orm.md
   ```
   Copy the indentation from line 100 exactly (10 spaces before `-`).
5. The advertised count becomes 49 in all five files, and nothing else on those lines changes:
   `(44 ADRs)` → `(49 ADRs)` in `CLAUDE.md:221`, `AGENTS.md:237`, `README.md:312`,
   `docs/index.md:299`; `(44 ADRs: 0001–0044)` → `(49 ADRs: 0001–0049)` in `GEMINI.md:165`.
   If a line number moved, find the quoted text instead.

## Where to change
- New: the five ADR files above (created by `bash -c`, never typed by hand).
- Edit with edit_file: `properdocs.yml`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`,
  `docs/index.md` (one line each, except `properdocs.yml`).

## Acceptance criteria
- [ ] `ls docs/architecture/decisions | wc -l` prints 49, and the last five names are the ones above.
- [ ] `head -1` of 0048 and 0049 starts `# 0048 —` and `# 0049 —`; `grep -c NNNN` on both prints 0.
- [ ] `grep -c '^### A[1-8]\.' docs/architecture/decisions/0045-*.md` prints 8, and
      `grep -c '^## Amendment — every seam has an in-memory fake' docs/architecture/decisions/0045-*.md` prints 1.
- [ ] Apart from line 1, 0048 equals the installer draft and 0049 equals the ORM draft:
      `sed 1d STORM/specs/ADR-installer.md > "$TMPDIR/a"; sed 1d docs/architecture/decisions/0048-vibey-install-installs-the-local-stack.md > "$TMPDIR/b"; diff "$TMPDIR/a" "$TMPDIR/b"`
      prints nothing (and the same for `ADR-orm.md` and 0049).
- [ ] `grep -c /private/tmp docs/architecture/decisions/004[5-9]-*.md` prints 0 for each file.
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta/test_adr_counts.py` passes (all 7 tests).
- [ ] `git diff --stat` touches only the five new files and the six edited files.

## Tests to write first (TDD)
None new. `tests/meta/test_adr_counts.py` (counts, contiguity, nav) is the test; run it before the
change to see it pass at 44, and after to see it pass at 49.

## Checks the lane must run (all must pass)
    ls docs/architecture/decisions | tail -1
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta/test_adr_counts.py tests/meta/test_phase_diagram.py
    grep -c /private/tmp docs/architecture/decisions/004[5-9]-*.md
    uv run --with 'properdocs==1.6.7' --with 'properdocs-theme-mkdocs==1.6.7' properdocs build --strict --site-dir "$TMPDIR/vibey-site"
If the pytest session fails at start because no PostgreSQL is reachable (the root
`tests/conftest.py:146-156` connects until `fakes-harness-decouple` lands), add `--noconftest`.
If `properdocs` cannot be installed (no network), say so in the verdict; do not skip silently.

## Out of scope
- Status lines, "accepted"/"proposed" wording and the notes these records owe on other ADRs
  (`gap-docs-adr-status-1`, `gap-docs-adr-status-2`; ADR-0046's own notes are its docs lane's).
- Editing the drafts in `STORM/specs/`, or any wording inside the landed records beyond step 3.
- Every other docs file.

Commit as `docs(adr): land ADR-0045, 0046, 0047, the installer ADR (0048) and the ORM ADR (0049)`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
