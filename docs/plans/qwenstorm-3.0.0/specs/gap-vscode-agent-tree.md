## Title
docs(agents): a fifth agent-surface tree for the VS Code adapter's agent extension, mirrored from the same skills and carrying SD-01

## Why
CLAUDE.md's "Agent-surface maintenance" rule keeps four mirrored trees of the project's skills:
`.claude/skills/<name>/SKILL.md` (the source), `.agents/skills/<name>/SKILL.md` (Codex),
`.cursor/rules/<name>.mdc` (Cursor, with a "Cursor rule mirror" note) and
`.agent/rules/<name>.md` (Antigravity, "Antigravity mirror of ..."). There are six skills:
`vibey-architecture`, `vibey-domain-model`, `vibey-engine-adapters`, `vibey-quality-gates`,
`vibey-releasing`, `vibey-testing`. ADR-0046 §8 (`specs/ADR-two-loops.md`) adds a VS Code
adapter to both loops, and an agent driven through VS Code receives none of this guidance and
no SD-01, which SD-01 §8 requires of "every agent it governs" (7.b,
`src/vibey_tools/gh/docs/doctrines.md:80`).

**Decision: this lane is gated, not keyed.** The directory an agent extension reads its rules
from, and the file format, belong to the extension, and the extension is not chosen until
V-VS2 records it (ADR-0046 *Verification owed*: "the agent extension used, with its licence
... and its source"). A configuration key could only default to a guess, and a tree written to
a guessed directory teaches no agent anything; 12.c (`doctrines.md:455`) asks for a key where a
value is a choice, and this one is a fact about the extension. So the lane waits for
`loops-vscode-verification`, and then the directory becomes declared state in the one place
the trees are already declared: the parity test's tree list (lane `gap-agent-tree-parity`).

## Required behaviour
1. Read the recorded V-VS2 result (lane `loops-vscode-verification`). It must name the agent
   extension, its OSI licence, and the workspace-relative directory and file suffix it reads
   project rules or instructions from, and whether a rules file needs front matter. **If the
   record does not name a rules directory, stop and report; do not choose one** (a bounded
   divergence under 9.c, `doctrines.md:351`: the operator decides).
2. For each of the six skills, create `<rules_dir>/<name><suffix>` whose body is exactly the
   body of `.claude/skills/<name>/SKILL.md` after its front matter, preceded by:
   - the extension's front matter, when the record says it needs one, carrying the source
     skill's `description` verbatim;
   - one line: `> **VS Code agent mirror** of \`.claude/skills/<name>/SKILL.md\`. When this guidance changes, update every agent-surface tree in the same PR.`
3. Carry SD-01 in the new tree exactly as lane `gap-sd01-carriage` carries it in
   `.cursor/rules/` (the same file name pattern and the same verbatim text), so the parity and
   carriage tests treat the fifth tree like the other four.
4. Add the new tree to the tree list that `gap-agent-tree-parity`'s meta-test declares (one
   entry: the directory, the suffix, and the header pattern above). Its parity checks then
   cover the fifth tree with no new test logic.

## Where to change
- New: six files under `<rules_dir>` (from the V-VS2 record), plus the SD-01 carrier file.
- Edit: the parity meta-test's tree list (`gap-agent-tree-parity`'s file under `tests/meta/`),
  one entry, with edit_file.
- Nothing under `src/`.

## Acceptance criteria
- [ ] `gap-agent-tree-parity`'s meta-test passes and lists five trees.
- [ ] `gap-sd01-carriage`'s meta-test passes and finds SD-01 verbatim in the fifth tree.
- [ ] For every skill, the new file's body (front matter and the mirror line removed) equals
      the source skill's body after its front matter, byte for byte; the parity meta-test is
      what asserts it.
- [ ] `git diff --stat` touches only the new tree and the one test file.

## Tests to write first (TDD)
None new: the parity and carriage meta-tests (lanes `gap-agent-tree-parity`,
`gap-sd01-carriage`) are the tests. Extend the parity test's declared tree list first, watch it
fail for the missing fifth tree, then add the files.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- The header sentences in the other four trees and CLAUDE.md's "Agent-surface maintenance"
  line, which name four trees (the docs wave, `gap-docs-*`, updates them).
- Provisioning a VS Code router file into BUILD worktrees (`gap-vscode-agent-router`).
- `.claude/skills` content, CHANGELOG.md, docs/, ADRs, AGENTS.md, GEMINI.md.

Commit as `docs(agents): a fifth agent-surface tree for the VS Code adapter`. Do not push.

## Lane card
- **Depends on:** `gap-agent-tree-parity`, `gap-sd01-carriage`, `loops-vscode-verification`
  (V-VS2 names the extension and its rules directory; this lane is gated on it).
- **Kind:** a docs lane: the named tree files plus one meta-test edit.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
