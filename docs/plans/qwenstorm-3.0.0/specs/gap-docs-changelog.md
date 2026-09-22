## Title
docs(changelog): the 2.1.0 and 3.0.0 sections, with every breaking change and the Forgejo data-loss warning

## Why
`CHANGELOG.md` has no 2.1.0 section and no 3.0.0 section (`issue-audit/gaps.md` M1, lines
625-628): `[Unreleased]` is at `CHANGELOG.md:13` and `[2.0.0]` at `:24`, while
`pyproject.toml:7` is `2.1.0` (released by `f26a28e1`). The vibey-releasing skill says
"a released version without an entry is a documentation bug" and nothing in the release path
writes the file (`.claude/skills/vibey-releasing/SKILL.md:191-198`). The operator wrote the
2.1.0 section as commit `d47c196d` ("docs(changelog): record 2.1.0", branch
`docs/changelog-2.1.0`), which is not in the integration branch.

3.0.0 is a breaking release (the gate is `gap-ops-release-3-0-0-gate`, item 9). Its section
must carry every `!` change, the Forgejo/Gitea data-loss warning, the OpenCode repeal and the
default-model change. The Forgejo facts are in `STORM/issue-audit/updates/327.md`: the chart
stops rendering the PVC `<release>-vibey-gitea-data`, so `helm upgrade` would delete it and
every repository on it, and Forgejo cannot reuse it (it migrates only from Gitea 1.22 or
earlier). SD-01 §6.1 forbids an irreversible action without explicit human approval, so the
warning leads the section.

## Required behaviour
1. **2.1.0.** If `grep -c '^## \[2.1.0\]' CHANGELOG.md` prints 1, leave that section as it is.
   Otherwise get the operator's text with `git show d47c196d:CHANGELOG.md` (if that object is
   missing, `git -C /private/tmp/claude-501/storm/changelog-2.1.0 show d47c196d:CHANGELOG.md`;
   if both fail, STOP and report BLOCKED). In it, the block from the line `## [Unreleased]`
   up to, not including, the line `## [2.0.0] (2026-09-21)` is the replacement. Replace the
   same block in `CHANGELOG.md` (from `## [Unreleased]` to just before `## [2.0.0]`) with it,
   with a checked replacement (EDITING-RULES rule 2).
2. **Collect the breaking changes.** Write `.qwenstorm/breaking.py` and run
   `python3 .qwenstorm/breaking.py`:
   ```python
   import re, subprocess
   out = subprocess.run(["git", "log", "--no-merges", "--reverse",
                         "--format=%h%x1f%s%x1f%B%x1e", "f26a28e1..HEAD"],
                        capture_output=True, text=True, check=True).stdout
   for rec in out.split("\x1e"):
       rec = rec.strip("\n")
       if not rec:
           continue
       short, subject, body = rec.split("\x1f", 2)
       bang = re.match(r"^([a-z]+)(?:\(([^)]*)\))?!: (.+)$", subject)
       note = re.search(r"^BREAKING[ -]CHANGE: (.+?)(?:\n\s*\n|\Z)", body, re.M | re.S)
       if bang or note:
           scope = (bang.group(2) or bang.group(1)) if bang else subject.split(":")[0]
           text = bang.group(3) if bang else subject.split(": ", 1)[-1]
           words = " ".join(note.group(1).split()) if note else ""
           extra = (" " + words[:1].upper() + words[1:]) if words else ""
           print(f"* **{scope}:** {text}.{extra} ({short})")
   ```
   Each printed line is one bullet, already in the file's format. Keep them in the printed order.
3. **3.0.0.** Directly above the line `## [2.1.0] (2026-09-21)`, insert this section (the
   heading's `(unreleased)` is replaced by the release commit's date when #316 is cut):
   ```
   ## [3.0.0] (unreleased)

   3.0.0 is a breaking release. It follows the sub-doctrines ratified on 2026-09-22: two loops
   at one instance per model (8.c); this era's default model, GPT-OSS 20B on Ollama (8.d); the
   test harness fed by a queue (8.e); every sovereign surface in one lane (8.f); always
   measured (8.g); Arch Linux and macOS as the default operating systems (8.h); and the thorough
   ledger (7.c). Sub-doctrine 8.b, amended by the same merge (#392), repeals OpenCode. Read the
   first entry before upgrading a Helm release.

   ### Before you upgrade a Helm release

   <FORGEJO>

   ### BREAKING CHANGES

   <OPENCODE>
   <the bullets from step 2>
   ```
   - `<FORGEJO>`: if `grep -c "this upgrade would delete the old Gitea volume" deploy/helm/vibey/templates/surfaces.yaml`
     prints 1 or more, write:
     ```
     * **helm (data loss risk):** the forge surface runs Forgejo, and `surfaces.gitea` is now `surfaces.forgejo` (rendering fails if the old key is set). The forge's volume is now `<release>-vibey-forgejo-data`. The old `<release>-vibey-gitea-data` volume is not reused — Forgejo migrates data only from Gitea 1.22 or earlier, and the chart ran `gitea/gitea:latest` — yet it holds every repository the old forge had. The chart no longer renders it, so Helm would delete it on upgrade; the chart therefore refuses to upgrade a release that still has it until a human decides. **Back the volume up first**, then either keep it with `kubectl annotate pvc <release>-vibey-gitea-data -n <namespace> helm.sh/resource-policy=keep` or delete it yourself, and run the upgrade again.
     ```
     Otherwise write:
     ```
     * **helm (data loss):** the forge surface runs Forgejo, and `surfaces.gitea` is now `surfaces.forgejo` (rendering fails if the old key is set). The forge's volume is now `<release>-vibey-forgejo-data`. The old `<release>-vibey-gitea-data` volume is not reused — Forgejo migrates data only from Gitea 1.22 or earlier — and the chart no longer renders it, so **`helm upgrade` deletes it and every repository on it.** Back it up before upgrading, and annotate it with `kubectl annotate pvc <release>-vibey-gitea-data -n <namespace> helm.sh/resource-policy=keep` if it must survive the upgrade.
     ```
   - `<OPENCODE>`: run `uv run python -c "from vibey.domain.config import DEFAULT_ENGINES; print(DEFAULT_ENGINES)"`
     (if that import fails, find the constant with `grep -rn "DEFAULT_ENGINES = " src/vibey/domain`
     and read its value; if there is none, STOP and report). Write:
     `* **engines:** OpenCode is repealed as an engine of either loop by sub-doctrine 8.b, ratified by the merge of #392; VS Code takes its place in both loops, and ADR-0046 §9 retires the runner once the VS Code adapter passes live conformance.`
     followed, on the same bullet, by ` The default engine pool no longer contains `opencode` (DEFAULT_ENGINES is <value>).`
     when the value has no `opencode`, or by ` The code has not yet followed: `opencode` is still in the default engine pool (DEFAULT_ENGINES is <value>) until ADR-0046's lanes land.`
     when it has. Put the value in backticks.
4. **[Unreleased]** keeps its heading and the single line `No changes yet.` Any other entry
   found under it (between `## [Unreleased]` and the next `## [`) moves to the end of the 3.0.0
   section, under its own subsection heading, unchanged.

## Where to change
- `CHANGELOG.md` only (over 800 lines: edit_file or checked replacements; never write_file).
- `.qwenstorm/breaking.py` (scratch, git-excluded; not committed).

## Acceptance criteria
- [ ] `grep -c '^## \[2.1.0\] (2026-09-21)' CHANGELOG.md` and `grep -c '^## \[3.0.0\] (unreleased)' CHANGELOG.md` print 1.
- [ ] The headings run, top to bottom: `[Unreleased]`, `[3.0.0] (unreleased)`, `[2.1.0]`, `[2.0.0]` …
- [ ] Every short hash that `python3 .qwenstorm/breaking.py` prints appears in `CHANGELOG.md`.
- [ ] `grep -c "resource-policy=keep" CHANGELOG.md` ≥ 1 and the Forgejo entry is the first
      bullet of the 3.0.0 section.
- [ ] `git diff --stat` shows only `CHANGELOG.md`, and no line of the `[2.0.0]` or older sections changed.

## Tests to write first (TDD)
None. The acceptance commands are the checks; the changelog has no meta-test.

## Checks the lane must run (all must pass)
    python3 .qwenstorm/breaking.py
    grep -n '^## \[' CHANGELOG.md | head -6
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    git diff --stat

## Out of scope
- Moving `(unreleased)` to a date: the release commit of #316 does that.
- Entries for non-breaking features and fixes of 3.0.0 beyond those under `[Unreleased]`.
- Every other file, including the vibey-gh tenant's own changelog.

Commit as `docs(changelog): the 2.1.0 and 3.0.0 sections, with every breaking change and the Forgejo data-loss warning`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
