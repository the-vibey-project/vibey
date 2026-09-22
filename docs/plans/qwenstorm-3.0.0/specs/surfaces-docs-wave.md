## Title
docs: ADR-0047 — every sovereign surface runs in one lane fed by RabbitMQ — with its measurement, and the docs for the lanes

## Why
Draft ADR-0047's "Owes" (`specs/ADR-surface-lanes.md`, line 5): the measurement named in §10,
recorded before the flip, and the docs wave: `docs/reference/cli.md` (`vibey surface
serve|ping|dead-letters|requeue`), `docs/reference/configuration.md` (`[surfaces]`,
`[surfaces.cache]`), `docs/plans/data-model.md` (`surface_operation`, `surface_dead_letter`),
`docs/plans/architecture-and-roadmap.md`, the paper's queue section, the four agent-surface trees,
CHANGELOG, and the ADR count (`tests/meta/test_adr_counts.py`). CLAUDE.md: "when a
skill/procedure changes, update Claude, Cursor, Codex, and Antigravity trees in the same PR", and
every code lane of this wave left these files to this lane (SPEC-TEMPLATE "Out of scope").
It lands **before** `surfaces-default-flip`, describing `direct` as the default and `queue` as
the opt-in, because the flip is gated on the operator's written acceptance that this lane's
evidence section asks for. This is ADR-0047 lane S34, owned by the docs wave, not a 20B lane.

## Required behaviour
1. **The ADR.** Land `specs/ADR-surface-lanes.md` as
   `docs/architecture/decisions/0047-every-sovereign-surface-runs-in-one-lane.md`, status
   *proposed* until the operator merges it, with these edits:
   - the surface names are the implemented ones (`configuration` for the config store, `siem`
     for security events) and the lane list is the implemented one (the `surfaces-*` slugs, in
     `specs/surfaces-queue.txt` order), in a new "Lanes" section;
   - a new **"Measured cache cost (Valkey)"** section: the two JSON files the operator produced
     with `scripts/bench_surface_lanes.py` (`surfaces-bench`) — macOS and Arch Linux — committed
     as `docs/architecture/decisions/evidence/0047/bench-macos.json` and `bench-arch.json`, and a
     table of their p50/p95/p99 and throughput beside the §10 estimates. **If the files do not
     exist yet, the section says "owed" and names the command; never invent a number** (10.f).
   - a line **"Operator's decision on the cache cost: owed"** — the operator replaces it, in
     writing, before `surfaces-default-flip` can run. This lane never writes the decision.
   - the decisions the lanes made where the draft was silent (list them under "Implementation
     decisions": the dedicated non-robust lease connection; the lease as its own interface; the
     shared `inspect_queue` owned by ADR-0045 T21; `adapter_timeout_seconds` and
     `dead_drain_batch`; parked outcomes always dead-lettered; ledger before acknowledgement; the
     caller scope and project-scoped ledger events; `configuration`/`siem` names; the reconciler
     classifying dead-lettered requests by body).
   Add it to the `properdocs.yml` nav, and update "(N ADRs" everywhere
   `tests/meta/test_adr_counts.py` checks (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`,
   `docs/index.md`) to the number of ADR files that exist after this one.
2. **`docs/reference/cli.md`**: `vibey surface serve [NAME | --all]`, `vibey surface ping
   [NAME | --all] [--json]`, `vibey surface dead-letters [--surface NAME] [--all] [--limit N]
   [--json]`, `vibey surface requeue ID [--by NAME]` — each with its exit codes (0, 1, 2, 3) and
   one runnable example (doctrine 3).
3. **`docs/reference/configuration.md`**: `[surfaces]` and `[surfaces.cache]` — every key,
   default, constraint and environment variable from `src/vibey/domain/config.py`
   (`SurfacesConfig`), and `[notifications] matrix`.
4. **`docs/plans/data-model.md`**: `surface_operation` and `surface_dead_letter` (migration
   0015), and the three ledger kinds `SurfaceOperationRecorded`, `SurfaceOperationParked`,
   `SurfaceOperationRequeued`; the relation count in the status note.
5. **`docs/plans/architecture-and-roadmap.md`**: the surface lanes in the container view and the
   process model (`vibey surface serve`, one Deployment per lane).
6. **`docs/guides/kubernetes.md`**: `surfaceLanes.*`, the credentials moving to the lanes, the
   Valkey cache image.
7. **`docs/paper.md`** queue section: surface lanes as the third queue family (jobs, tests,
   surfaces); keep `tests/meta/test_paper_evidence.py` green.
8. **CLAUDE.md, AGENTS.md, GEMINI.md** and the four agent-surface trees (`.claude/skills/`,
   `.cursor/rules/`, `.agents/skills/`, `.agent/rules/`: architecture, engine-adapters, testing,
   quality-gates): the surface lanes, the Valkey cache, the `integration` services
   (`VIBEY_TEST_AMQP_URL`, `VIBEY_TEST_CACHE_URL`).
9. **`CHANGELOG.md`** through the release tooling's usual path.

## Where to change
- The files above only.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes (ADR counts and nav, paper render and evidence, phase diagram).
- [ ] The book and paper build as in the docs job.
- [ ] The ADR's measurement section holds real JSON or says "owed" with the command; its decision line says "owed".

## Tests to write first (TDD)
- None: the doc meta-tests are the tests.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Code. The operator's decision on the cache cost and any canon text (Article II.3: the
  operator's merge). The default flip (`surfaces-default-flip`) and the docs lines it changes
  (`surfaces-docs-flip`).

## Lane card
- **Depends on:** `surfaces-bench`, `surfaces-cluster-smoke`, `surfaces-contracts-lane`, `surfaces-cli-dead-letters`, `surfaces-callers-registry` (every lane whose behaviour it documents).
- **Shares a file with:** the ADR count lines and the agent trees (every docs wave). Keep their edits.
- **Must keep passing unchanged:** `tests/meta/test_adr_counts.py`, `tests/meta/test_paper_renders.py`, `tests/meta/test_paper_evidence.py`, `tests/meta/test_phase_diagram.py`.
- **Standing constraints:** evidence is bounded (10.f): no number that a run did not produce; the four agent trees change together.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
