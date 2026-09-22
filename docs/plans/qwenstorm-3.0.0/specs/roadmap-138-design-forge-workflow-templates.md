## Title
docs(design): draft the ADR for rendering vibey-gh's managed workflow set per forge, Forgejo Actions first

## Why
Issue #138 (rewrite: `issue-audit/updates/138.md`, Scope 4 and "Proposed child issues" 3, marked
"Design needed first"): "The managed automation (workflow templates) is rendered per forge from
the same doctrine-bearing sources: GitHub Actions (today), Forgejo Actions, and GitLab CI."
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, and `:168-177` requires one vibey-owned protocol per surface. Today every managed
template is GitHub Actions only: the 17 files in `src/vibey_tools/gh/vibey_gh/templates/workflows/`,
rendered by `install.render_workflow` (`vibey_gh/install.py:198-300`, placeholder substitution such
as `__VIBEY_GH_CONVERSATION_TRIGGER__` at `:287`) into `.github/workflows/`, and drift-checked by
`install.installed` (`install.py:620`; CI at `.github/workflows/ci.yml:712-727`). The forge wave's
own spec leaves "every `gh` invocation inside the rendered workflow templates" GitHub-only
(`specs/forge-adapter.md`, appendix item 7) and warns that gate names on Forgejo Actions carry an
event suffix (appendix item 4). gaps.md §L8 proposes the implementation lane "workflow templates
render for Forgejo Actions"; this spike is its design input, so that lane is not guessed.

This is a design spike: the deliverable is one draft ADR. No code changes.
**Implementer: a large model or the operator (design, not code); like `gap-spike-*`, the storm
runner skips `roadmap-*-design-*`.**

## Required behaviour
1. Write exactly one file:
   `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-138-forge-workflow-templates.md`.
   Change no file in the lane's clone and commit nothing.
2. Ground every claim about this repository in a `path:line` you read in the clone. Anything
   about Forgejo Actions or GitLab CI that the tree cannot prove (syntax support, `workflow_run`,
   `concurrency`, reusable actions, the action registry, runner labels, secrets API, the check
   name suffix) is written as a **Verification owed** item, never as a fact.
3. Inventory every template: for each of the 17 files, list the GitHub-only constructs it uses
   (read each file): `workflow_run` chaining, `gh` CLI calls, `actions/*` and third-party `uses:`
   references, `GITHUB_TOKEN` permissions blocks, `concurrency`, `$GITHUB_STEP_SUMMARY`,
   `github.event.*` fields, and required-check names. Present it as a table.
4. Weigh at least these options, each with consequences for drift tests, 12.c and 10.e:
   - (A) one template tree plus a per-forge *dialect* pass in `render_workflow` (placeholders
     for the forge-specific pieces);
   - (B) a second template tree `templates/workflows-forgejo/` rendered into `.forgejo/workflows/`;
   - (C) templates call only `vibey-gh` subcommands for every forge interaction (the adapter does
     the forge work), leaving the YAML itself nearly forge-neutral.
   Recommend one in `## Decision`, with the install destination per forge and how `installed()`
   checks drift for each.
5. GitLab CI is not designed here. Quote #138's open question 4 verbatim in
   `## Open decisions for the operator`: "**GitLab priority:** with GitLab now declared-only,
   should GitLab CI templates wait until an adopter asks?"

## Where to change
- Create only `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-138-forge-workflow-templates.md`
  (Markdown; no provenance header needed for a Markdown draft outside the clone).
- Read: `vibey_gh/templates/workflows/*.yml`, `vibey_gh/install.py`, `vibey_gh/config.py`
  (`WorkflowNamesConfig`, `[install] workflows`), `test/test_templates.py`,
  `.github/workflows/ci.yml:696-727`, `specs/forge-adapter.md` (appendix), gaps.md §L6–§L8.

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# Rendering the managed workflow set per forge` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:** 2026-09-22` (or the day written), `**Cites:**` naming 8.b
      (`doctrines.md:138-139`, `:168-177`), 12.c (`doctrines.md:455`), 10.e (`doctrines.md:417`),
      vibey-gh ADR 0001 and ADR 0002.
- [ ] `## Context` with the template inventory table (item 3) and at least 12 verified `path:line` anchors.
- [ ] `## Options considered` with options A, B and C (item 4), each with consequences.
- [ ] `## Decision` naming one option, the destination directory per forge, how drift is
      checked per forge, and how required-check names are kept equal to what the gate reads.
- [ ] `## Consequences` (good and bad).
- [ ] `## Lanes this unblocks`: a table (slug-to-be, title, one-line scope, files) of 20B-sized
      lanes, e.g. the dialect pass, the first Forgejo-rendered template, its drift test.
- [ ] `## Open decisions for the operator` with #138 open question 4 quoted verbatim, unanswered.
- [ ] `## Verification owed`: every external Forgejo/GitLab fact, each with how to verify it
      against a live Forgejo runner (the chart surface of #327, `chart-operator-forgejo-p2`).

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
    python3 -c 'import re; from pathlib import Path; p = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-138-forge-workflow-templates.md"); assert p.is_file(), "the ADR draft was not written"; text = p.read_text(encoding="utf-8"); assert text.startswith("# Rendering the managed workflow set per forge"), "wrong title line"; required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context", "## Options considered", "## Decision", "## Consequences", "## Lanes this unblocks", "## Open decisions for the operator", "## Verification owed", "should GitLab CI templates wait until an adopter asks?"]; missing = [h for h in required if h not in text]; assert not missing, f"missing: {missing}"; anchors = re.findall(r"[\w./-]+\.(?:py|yml|yaml|toml|md):\d+", text); assert len(anchors) >= 12, f"only {len(anchors)} path:line anchors"; leftover = [w for w in ("TBD", "TODO", "lorem") if w in text]; assert not leftover, f"placeholder(s) left in the draft: {leftover}"; print("ADR draft complete")'
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- Any change to templates, `install.py` or tests (the gaps.md §L8 implementation lane).
- GitLab CI and Bitbucket Pipelines designs (#138 Q4; #298 is blocked).
- The tree's `docs/` and ADR directories. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
