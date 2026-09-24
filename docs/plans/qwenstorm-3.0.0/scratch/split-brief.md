# Brief for every split-spec writer (QwenStorm 3.0.0 issue audit)

STORM = the storm root, $VIBEY_STORM_HOME/qwenstorm-3.0.0 (on macOS by default ~/git/vibey-storm/qwenstorm-3.0.0)

You write lane specs only. Do NOT edit code, do NOT edit anything under STORM/integration, do NOT
edit STORM/issue-audit/ or any existing spec, do NOT file issues, push, or run git commands that
write. Write ONLY the spec files you are assigned.

## Read first, in this order
1. STORM/STORM-CONTEXT.md: settled law, operator standards and rulings. It wins over anything older,
   including the audit files.
2. STORM/SPEC-TEMPLATE.md: the required format and the implementer's profile.
3. STORM/EDITING-RULES.md: what the implementing lane is told about editing files.
4. Your parent audit file(s): STORM/issue-audit/updates/<N>.md. Line 1 is the audit verdict and the
   corrections it demands; line 2 is the title; the body is the audited, corrected spec of child 1;
   the section "## Proposed child lanes" at the end gives every child's scope and dependencies.
   Where a parent body has a "Conventions this lane relies on" or "Standing constraints" section,
   the children need those texts too.

## The implementer
A local gpt-oss:20b (Ollama, 131k context, ~40 turns, tools read_file/write_file/edit_file/shell)
sees ONLY your one spec file plus the repository. It succeeds on narrow exact lanes and fails on
broad ones. A reviewer then verifies the diff against your spec.

## What each file must be
Path: STORM/specs/<slug>.md, slug exactly as assigned.

Line 1: `<!-- split of #<parent>: child <n> of <k>; audit: issue-audit/updates/<parent>.md -->`
Then these sections, with these exact headings, in this order:
- `## Title` (one Conventional Commit title, `!` when breaking)
- `## Why` (2-5 sentences; cite the ratified rule and file:line evidence)
- `## Required behaviour` (numbered, testable)
- `## Where to change` (exact files, classes, functions, file:line anchors, the pattern to copy;
  every new class gets an interface beside it, ADR-0016)
- `## Acceptance criteria` (checklist; each item a command or a test name)
- `## Tests to write first (TDD)` (test file paths, test names, what each asserts)
- `## Checks the lane must run (all must pass)` (a COMPLETE fenced bash block, written out in full)
- `## Out of scope`
- optional `## Conventions this lane relies on (everything needed is here)` or
  `## Standing constraints` when the child needs them
- `**Depends on:** <slug>, <slug>` (the exact slugs assigned to you below, or `none`), followed by
  one short line per slug saying what the lane uses from it
- last: `## Hard repository rules (always)` then the line
  `See STORM/SPEC-TEMPLATE.md.`

## Self-contained, always
- Inline every verb/method signature, dataclass, constant, exact message text, convention (e.g. the
  forge wave's C1/C6/C7/C8), test-double description and the full check block the child needs.
- Never write "as above", "as specified above", "same block as Part 0a", "the Part 1 block",
  "see the parent issue", "see specs/forge-adapter.md", "see #NNN's spec", or end a failure text
  with "…". The child cannot see those texts (the forge audits proved this).
- Child 1 is the parent's own body: transcribe it faithfully into the template (it is already
  audited), changing only what the template needs, what drifted, and its Depends-on line.
- Children 2..k: expand the audit's scope paragraph into a full spec with the same precision as
  child 1: exact files (one source file + its interface + one test file where possible; if the
  scope must span more, name every file and say why), signatures, failure texts, numbered
  behaviours, tests, check block, out of scope.
- Keep EVERY correction the audit made (its line 1 and body): substitution only at declared seams
  (constructor/keyword injection, the conftest fixtures it names) and never monkeypatch.setattr of
  an import or module/class attribute, mock.patch, MagicMock or AsyncMock (9.b, D7); an in-memory
  fake for every new port; ORM-only persistence, no new raw SQL (D6); OpenCode repealed, no new test
  parametrizes opencode (D4); sovereign defaults (8.b); Arch Linux and macOS (8.h); configurable
  values, no new hard-coded constants that could be keys (12.c); `--no-cov` on partial tenant runs;
  the tenant `packages` entries where a test enforces them; protected tests never edited.
- Verify every file:line anchor you keep against the integration clone STORM/integration
  (branch storm/integration, HEAD 4317cff6; read it with Read/Grep/`git -C ... show`). The audit
  was taken at 739536ea; if a line moved, write the current line. Never read /Users/adam/git/vibey
  (stale). The integration branch now carries the repository's `[platform] kind = "github"`
  declaration (d3b4a388), so the forge wave's "operator prerequisite" is met on integration; the
  lane must still never write or change that declaration.
- No placeholders, no TODOs.

## Your final message
Per file: path, title, the Depends-on line, and how many files the lane touches. Then every gap:
a claim you could not verify, a line reference you corrected, a scope you could not fit in one
source file, or a conflict with STORM-CONTEXT. Under 300 words.
