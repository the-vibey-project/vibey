## Title
docs(design): draft the ADR for the human-facing VS Code extension — toolchain, location, CI on Arch Linux and macOS, Open VSX first

## Why
Issue #290 (rewrite: `issue-audit/updates/290.md`, "Scope / Required behaviour (this issue: the
human-facing extension)" and "Proposed child issues" 1, marked "Design needed first"). The operator
asked on 2026-09-18: "make a vscode plugin for vibey please". On that date VS Code was not yet an
engine; sub-doctrine 8.b made it one only on 2026-09-22 (`src/vibey_tools/gh/docs/doctrines.md:128-135`).
So the literal ask is an editor extension a human uses to drive vibey. The engine half is not this
spike: it is ADR-0046 §8 (`specs/ADR-two-loops.md:263-285`) and its lanes (L20; the verification
V-VS1–V-VS5 is gaps.md §B1), and the installer entries already exist as `specs/installer-vscode.md`.

The ruled editors (STORM-CONTEXT, operator rulings 2026-09-22): sovereignloop's VS Code is
Code - OSS / VSCodium (Arch `code`, macOS `vscodium` cask, binary `codium`); Microsoft's build is
`vscode-paid`, for paidloop. An extension's sovereign distribution channel is therefore Open VSX
(VSCodium's registry); Microsoft's marketplace is a declared extra (8.a/8.b). 8.h
(`doctrines.md:326-333`) requires Arch Linux and macOS. 2.b (`doctrines.md:30`) requires publishing
by the same automation as everything else. Doctrine 3 (`doctrines.md:32-35`) requires an example
per exposed command.

The tree has no TypeScript and no Node lane: `git ls-files '*.ts' '*.tsx' 'package.json'` is empty,
and the only `node` in CI is the image contract that forbids it in the runtime image
(`.github/workflows/ci.yml:781-790`). The machine-readable CLI surfaces a first slice can use exist:
`vibey status --json` (`src/vibey/cli/main.py:709-712`) and `vibey answer --raw`
(`main.py:292-306`). An HTTP API is #143 (`roadmap-143-api-*`), not yet built.

This is a design spike: the deliverable is one draft ADR. No code changes.
**Implementer: a large model or the operator (design, not code); like `gap-spike-*`, the storm
runner skips `roadmap-*-design-*`.**

## Required behaviour
1. Write exactly one file:
   `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-290-vscode-extension.md`.
   Change no file in the lane's clone; commit nothing.
2. Decide, with reasons: the language (TypeScript, since the VS Code extension API is a
   JavaScript API), the Node version pin and where it is declared (12.c), the packaging tools
   (`vsce` for Microsoft's marketplace, `ovsx` for Open VSX), the test runner, and where the
   extension lives (propose `clients/vscode/`, and say how it relates to #143's clients).
3. The CI lane: a new job on Arch Linux (container `archlinux:base-devel`) and macOS, which builds,
   lints and tests the extension; how it becomes a required check (`.vibey-gh.toml` rulesets); how
   the root `vibey` image contract (`ci.yml:781-790`) keeps Node out of the runtime image.
4. Publishing: Open VSX first (the sovereign path), Microsoft's marketplace declared-only; which
   credentials are needed and where they live (the secrets surface; never a workflow literal); how
   vibey-gh's release automation publishes both (2.b).
5. The first slices: a read-only tree view from `vibey status --json` on an interval; gate answering
   through `vibey answer` (choices, `--defaults`, `--raw`); later slices on #143's API. Nothing needs
   an account.
6. Quote #290 open question 1 verbatim in `## Open decisions for the operator`: "**Which did you
   mean by "vscode plugin"?** (a) an extension a human uses to drive vibey, (b) VS Code as an engine
   (now canon), or (c) both? This rewrite assumes (c), split into two issues." Also quote open
   question 3 (the registry). The ADR records that the extension is the literal 2026-09-18 ask and
   does not answer the questions.
7. Facts about VS Code, VSCodium, Open VSX or `vsce`/`ovsx` that the tree cannot prove are
   **Verification owed** items, never asserted.

## Where to change
- Create only the ADR draft above (Markdown, outside the clone).
- Read: `src/vibey/cli/main.py` (status, answer, watch), `.github/workflows/ci.yml`,
  `.vibey-gh.toml` (`[rulesets.*]`), `src/vibey_tools/gh/vibey_gh/github_release.py`,
  `docs/runbooks/expansion/08-clients.md`, `specs/installer-vscode.md`, `specs/ADR-two-loops.md` §8.

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# The human-facing VS Code extension` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:**`, `**Cites:**` naming 8.a (`doctrines.md:99`), 8.b
      (`doctrines.md:128-135`), 8.h (`doctrines.md:326-333`), 2.b (`doctrines.md:30`), doctrine 3
      (`doctrines.md:32-35`), 12.c (`doctrines.md:455`), ADR-0046 §8.
- [ ] `## Context` with at least 10 verified `path:line` anchors.
- [ ] `## Options considered` (at least: in this repository vs a separate repository (ADR-0021/0037
      say one tree); shelling out to the CLI vs waiting for #143's API; Open VSX only vs both registries).
- [ ] `## Decision` covering items 2–5.
- [ ] `## CI lane` (item 3) and `## Publishing` (item 4) as their own sections.
- [ ] `## Consequences`.
- [ ] `## Lanes this unblocks`: a table of 20B-sized lanes (slug-to-be, title, scope, files): the
      skeleton and CI job, the status view, gate answering, publishing.
- [ ] `## Open decisions for the operator` with #290 open questions 1 and 3 quoted verbatim.
- [ ] `## Verification owed` (item 7).

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
    python3 -c 'import re; from pathlib import Path; p = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-290-vscode-extension.md"); assert p.is_file(), "the ADR draft was not written"; text = p.read_text(encoding="utf-8"); assert text.startswith("# The human-facing VS Code extension"), "wrong title line"; required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context", "## Options considered", "## Decision", "## CI lane", "## Publishing", "## Consequences", "## Lanes this unblocks", "## Open decisions for the operator", "## Verification owed", "Which did you mean by"]; missing = [h for h in required if h not in text]; assert not missing, f"missing: {missing}"; anchors = re.findall(r"[\w./-]+\.(?:py|yml|yaml|toml|md):\d+", text); assert len(anchors) >= 10, f"only {len(anchors)} path:line anchors"; placeholders = [w for w in ("TBD", "lorem") if w in text]; assert not placeholders, f"placeholders left in the draft: {placeholders}"; print("ADR draft complete")'
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- The VS Code engine adapter, V-VS1–V-VS5, OpenCode's retirement (ADR-0046 lanes; gaps.md §B1–§B3).
- Any code, workflow or config change; installer entries (`installer-vscode`).
- The tree's `docs/` and ADR directories. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
