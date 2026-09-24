## Title
docs(design): draft the ADR for how a discovery proposal parks as a human gate before any project exists, and how accepting it creates the project

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, Scope 5 "Candidates reach the conductor as
**proposals that park as human gates**. Accepting one runs `vibey new` with the provenance
attached", Acceptance "No project is created without a recorded human acceptance (test)",
"Proposed child issues" 7). The operator's constraint: "Proposals are proposals — a human accepts
before the conductor spends a cycle." The non-negotiable (CLAUDE.md): "Never block a worker on a
human. Human input is a parked job plus a `human_gate` row" (ADR-0009). But a gate today cannot
exist without a project: `human_gate.project_id uuid NOT NULL REFERENCES project(id)`
(`migrations/0008_human_gate_artifact_budget.sql:1-14`), and `HumanGateRequest`/`HumanGateRecord`
(`src/vibey/application/dto.py:85-100`) carry a project. Creating a project in order to park its
proposal would break the acceptance criterion. This is a real design gap, not an operator question,
so it is a spike. Sub-doctrines 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`: the proposal,
the decision and the actor are ledger material) and 12.c (`doctrines.md:455`) bind it; the ORM
standard (STORM-CONTEXT: SQLAlchemy through the `orm-*` seams, no new raw SQL) binds any new table.

This is a design spike: the deliverable is one draft ADR. No code changes.
**Implementer: a large model or the operator (design, not code); like `gap-spike-*`, the storm
runner skips `roadmap-*-design-*`.**

## Required behaviour
1. Write exactly one file:
   `STORM/specs/ADR-roadmap-87-proposal-gates.md`.
   Change no file in the lane's clone; commit nothing.
2. Read the gate machinery end to end and cite it: the table (`migrations/0008`), the DTOs
   (`dto.py`), the repository (`src/vibey/infrastructure/db/human_gate_repository.py` and the
   `orm-human-gate` spec), `vibey answer` (`src/vibey/cli/main.py:292-330`), how a parked job
   resumes (`src/vibey/application/worker.py`), and the ledger's append rules.
3. Weigh at least these options, each against the acceptance criterion, ADR-0009, the append-only
   ledger, idempotency under replay, and the ORM standard:
   - (A) a **proposal inbox**: a new `proposal` table (id, candidate provenance, status, decided_by,
     decided_at) with its own `vibey proposals list|accept|decline`, no project until accepted;
   - (B) **nullable `project_id` on `human_gate`** with a proposal gate kind, keyed by a proposal id;
   - (C) a **holding project** (one per deployment) whose gates are proposals, with accepted ones
     spawning real projects;
   - (D) proposals as **ledger events only** (a `ProposalRaised`/`ProposalDecided` pair on a
     deployment-level stream), with acceptance replaying `vibey new` from the event.
4. `## Decision`: recommend one, and state exactly: the table or event shape, the gate kind name,
   who may accept (the operator's `vibey answer` identity; any answer is recorded with its actor),
   how acceptance calls the intake with `Candidate.intake_arguments()`
   (`roadmap-87-explorer-candidate`) so provenance is recorded by `roadmap-87-intake-provenance`,
   how a replayed acceptance creates exactly one project, and what declining records.
5. Out of the ADR's scope, and said so: how candidates are found (#87 open question 2), FOSS/paid
   classification (open question 1), rate caps (open question 3).

## Where to change
- Create only the ADR draft above (Markdown, outside the clone).

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# Proposals that park before any project exists` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:**`, `**Cites:**` naming ADR-0009, 7.c (`doctrines.md:82-91`),
      12.c (`doctrines.md:455`), 9.b (`doctrines.md:349`), and the non-negotiables it touches.
- [ ] `## Context` with at least 10 verified `path:line` anchors, including
      `migrations/0008_human_gate_artifact_budget.sql:3`.
- [ ] `## Options considered` with A–D, each with consequences.
- [ ] `## Decision` covering every point of item 4.
- [ ] `## How each non-negotiable still holds` (never block a worker; idempotent under replay;
      append-only ledger).
- [ ] `## Consequences`.
- [ ] `## Lanes this unblocks`: 20B-sized lanes (slug-to-be, title, scope, files), including any
      migration (next free number; 0016 or later) and its ORM table.
- [ ] `## Open decisions for the operator`: quote #87 open questions 1, 2 and 3 verbatim as out of
      scope and unanswered.
- [ ] `## Verification owed`.

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
    python3 -c 'import re; from pathlib import Path; p = Path("STORM/specs/ADR-roadmap-87-proposal-gates.md"); assert p.is_file(), "the ADR draft was not written"; text = p.read_text(encoding="utf-8"); assert text.startswith("# Proposals that park before any project exists"), "wrong title line"; required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context", "## Options considered", "## Decision", "## How each non-negotiable still holds", "## Consequences", "## Lanes this unblocks", "## Open decisions for the operator", "## Verification owed", "0008_human_gate_artifact_budget.sql:3"]; missing = [h for h in required if h not in text]; assert not missing, f"missing: {missing}"; anchors = re.findall(r"[\w./-]+\.(?:py|sql|toml|md):\d+", text); assert len(anchors) >= 10, f"only {len(anchors)} path:line anchors"; placeholders = [w for w in ("TBD", "lorem") if w in text]; assert not placeholders, f"placeholders left in the draft: {placeholders}"; print("ADR draft complete")'
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- Any code, migration or test; discovery sources; classification; rate caps.
- The tree's `docs/` and ADR directories. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
