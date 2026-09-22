## Title
docs(design): draft the ADR analysing starvation, aging and fairness of the job claim order before and after RabbitMQ dispatch

## Why
Issue #301 (rewrite: `issue-audit/updates/301.md`, workstream 4 "starvation and fairness", "Proposed
child issues" 6, marked "Design needed first — Analyse strict priority under the post-ADR-0044 claim
order, with a simulation test"). The paper's *Queue semantics* section (`docs/paper.md:163-184`)
states the claim order; its claims must agree with the implementation (the issue's acceptance bar;
10.f, `src/vibey_tools/gh/docs/doctrines.md:419`). Today the claim is strict priority:
`ORDER BY j.priority DESC, j.run_after ASC, j.id ASC … FOR UPDATE SKIP LOCKED`
(`src/vibey/infrastructure/db/job_repository.py:198-199`), indexed by
`job_claim ON job (project_id, priority DESC, run_after ASC, id ASC)` (`migrations/0003_job.sql:32`).
Strict priority can starve a low-priority job indefinitely while higher-priority work keeps
arriving; nothing ages. ADR-0044 (proposed) and the `rmq-*` lanes move dispatch to RabbitMQ
(`STORM/specs/rabbitmq-lanes.md`; the claim path after the move is `rmq-r16-rabbitmq-job-repository`),
and 8.c (`doctrines.md:196-234`) makes each loop a single instance per model fed by a queue, which
changes the service discipline again. The analysis must be done before any code or paper claim.

This is a design spike: the deliverable is one draft ADR. No code changes.
**Implementer: a large model or the operator (design, not code); like `gap-spike-*`, the storm
runner skips `roadmap-*-design-*`.**

## Required behaviour
1. Write exactly one file: `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-301-fairness.md`.
   Change no file in the lane's clone; commit nothing.
2. **Model both disciplines precisely**, citing code and specs: (a) today's PostgreSQL claim
   (`job_repository.py:160-210`, the lease and reaper); (b) the post-ADR-0044 path — how a job
   reaches a consumer (publish order, per-project queues, prefetch, redelivery, dead-letter), read
   from `STORM/specs/rmq-r06-job-dispatch-envelope.md`, `rmq-r12-queue-topology.md`,
   `rmq-r14-project-deliveries.md`, `rmq-r16-rabbitmq-job-repository.md` and `ADR-rabbitmq-queue.md`.
   State whether RabbitMQ priority queues (`x-max-priority`) are used, and what order a single
   consumer at prefetch 1 then observes.
3. **Starvation analysis**: for each discipline, the condition under which a job waits unboundedly
   (arrival rate of higher-priority work vs service rate), stated as an inequality over named
   quantities; whether leases/redelivery can reorder work; per-project isolation.
4. **Options**: at least (i) keep strict priority and state the starvation bound as a documented
   limit; (ii) aging (effective priority rises with wait, with a declared rate — 12.c); (iii) weighted
   fair queuing across priorities; (iv) per-priority queues with a guaranteed share. Each with its
   cost on the invariants (idempotent under replay; capacity rejection outranks completion).
5. **`## Lanes this unblocks`** must include a deterministic simulation test lane: a pure,
   seeded discrete-event simulator in `tests/` (stdlib only) that drives the chosen discipline with
   a declared arrival trace and asserts the stated bound — with its exact module name, inputs and
   assertions.
6. Quote #301 open question 4 verbatim in `## Open decisions for the operator`: "**Paper cutoff
   versus substrate churn:** should the paper describe the system as of a fixed release (for example
   the first release with RabbitMQ dispatch), or keep chasing develop?" — unanswered.

## Where to change
- Create only the ADR draft above (Markdown, outside the clone).

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# Starvation, aging and fairness of the claim order` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:**`, `**Cites:**` naming ADR-0002, ADR-0044, 8.c
      (`doctrines.md:196-234`), 8.g (`doctrines.md:316-324`), 10.f (`doctrines.md:419`), 12.c (`doctrines.md:455`).
- [ ] `## Context` with at least 10 verified `path:line` anchors, including
      `job_repository.py:198` and `0003_job.sql:32`.
- [ ] `## Model: PostgreSQL claim` and `## Model: RabbitMQ dispatch` (item 2).
- [ ] `## Starvation analysis` with an explicit inequality per discipline (item 3).
- [ ] `## Options considered` (item 4), `## Decision`, `## Consequences`.
- [ ] `## Lanes this unblocks` including the simulation lane (item 5).
- [ ] `## Open decisions for the operator` with #301 open question 4 verbatim.
- [ ] `## Verification owed` (anything about RabbitMQ ordering the specs do not settle).

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
    python3 - <<'PY'
    import re
    from pathlib import Path
    p = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-301-fairness.md")
    assert p.is_file(), "the ADR draft was not written"
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# Starvation, aging and fairness of the claim order"), "wrong title line"
    required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context",
                "## Model: PostgreSQL claim", "## Model: RabbitMQ dispatch",
                "## Starvation analysis", "## Options considered", "## Decision",
                "## Consequences", "## Lanes this unblocks", "## Open decisions for the operator",
                "## Verification owed", "Paper cutoff versus substrate churn",
                "job_repository.py:198", "0003_job.sql:32"]
    missing = [h for h in required if h not in text]
    assert not missing, f"missing: {missing}"
    anchors = re.findall(r"[\w./-]+\.(?:py|sql|md|toml):\d+", text)
    assert len(anchors) >= 10, f"only {len(anchors)} path:line anchors"
    for word in ("TBD", "lorem"):
        assert word not in text, f"placeholder {word!r} left in the draft"
    print("ADR draft complete")
    PY
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- Any code, the simulator itself, and the paper text (docs wave). Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
