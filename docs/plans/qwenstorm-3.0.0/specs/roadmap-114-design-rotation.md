## Title
docs(ledger): draft the ADR for rotating the ledger through its storage tiers without breaking append-only

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, Scope 2: "**Rotation** runs as a queued job
… creates range partitions ahead of `seq`, moves records raw → compressed → archive, and
verifies each copy before removing the source. The job is idempotent under replay", and
"Proposed child issues" 4). Nothing can be specified for it yet, because the parts contradict
each other on the current schema:
- **Append-only is a non-negotiable** (CLAUDE.md: "The ledger is append-only. No updates, no
  deletes. Corrections are new events that supersede prior ones"; sub-doctrine 7.c,
  `src/vibey_tools/gh/docs/doctrines.md:82-91`: "completeness grows by new events, never by
  rewriting old ones"). It is enforced by two rules that turn UPDATE and DELETE of `event` into
  nothing (`migrations/0013_ledger_partitioning.sql:63-66`), pinned as silent no-ops by
  `tests/infrastructure/db/test_ledger_repository.py:125-154`, and — once `orm-ledger-guard`
  lands — refused loudly at the ORM seam (`AppendOnlyGuard`, draft ADR `specs/ADR-orm.md` §5).
- Yet the issue wants raw records to **leave the hot table** once a verified compressed copy
  exists, and the in-memory tier manager already does exactly that
  (`src/vibey/infrastructure/ledger/tier_manager.py:58-68`, `remove_raw` at `:68`).
- `event` is `PARTITION BY RANGE (seq)` (`0013:35`) with one DEFAULT partition (`0013:37-41`),
  and `seq` is **per project** (`migrations/0002_event.sql:30-33`, claimed by `append_event`,
  `0013:84-114`). A per-project window ("the latest N raw per project") does not align with a
  seq-range partition: every new project writes seq 1 again.

This is a real design gap, not an operator question, so it is a spike. Whatever is decided must
keep the no-loss gate sound (R6, `src/vibey/domain/noloss.py:149-172`, over the gapless `seq`),
keep every job idempotent under replay, never block a worker on a human, and go through the ORM
standard (no new raw SQL outside migrations). The deliverable is one draft ADR; no code.

## Required behaviour
1. Write exactly one file:
   `STORM/specs/ADR-roadmap-114-rotation.md`.
   Change no file in the lane's clone; commit nothing.
2. Read, and cite with `path:line` anchors you have read yourself in the clone:
   `migrations/0002_event.sql`, `migrations/0009_event_produced_at.sql`,
   `migrations/0013_ledger_partitioning.sql`, `src/vibey/domain/ledger_tier.py`,
   `src/vibey/domain/ledger_chain.py:13-26` (the chain is derived, and "How the storage tiers
   fold over it"), `src/vibey/infrastructure/ledger/tier_manager.py`,
   `src/vibey/infrastructure/ledger/tier_store.py`,
   `src/vibey/infrastructure/ledger/interfaces/tier_store_interface.py` (synchronous; `put_raw`,
   `remove_raw`), `src/vibey/domain/job.py:66-68` (`idempotency_key`),
   `src/vibey/application/dto.py:19-33` (`EnqueueRequest`; a job needs a `phase`, `:23`),
   `src/vibey/bootstrap.py:274-287` (`_KIND_LEASES`, `lease_for_kind`), `:488` and `:618-625`
   (the handler table and dispatcher), `src/vibey/domain/noloss.py:149-172`,
   `src/vibey/domain/ledger.py:37` (`EventKind`) and `:217-224` (`digest_range`),
   `src/vibey/infrastructure/postgres.py:28` (PostgreSQL floor 14) and
   `.github/workflows/ci.yml:151` (the 14–18 matrix). Also read the storm specs this ADR
   builds on and cite them by file: `specs/roadmap-114-tier-config.md` (N ≥ 1, `archive_tier`,
   `archival_node`), `specs/roadmap-114-postgres-tier-store-p1.md` (the append-only
   `ledger_segment` table, migration 0016), `-p3.md` (the async `LedgerSegmentStore` port),
   `specs/roadmap-114-tier-aware-reads-p3.md` (reads merge raw rows and segments, raw wins),
   `specs/orm-ledger-guard.md`, and `specs/ADR-rabbitmq-queue.md` (the job queue).
3. Establish these facts in `## Context`, each with its evidence:
   - F1. A bounded range partition cannot be added while the DEFAULT partition holds a row in
     its range, so "partitions ahead of `seq`" can only be created above the highest seq of
     **every** project.
   - F2. `ALTER TABLE … DETACH PARTITION … CONCURRENTLY` is refused while a DEFAULT partition
     exists; a plain DETACH takes a stronger lock on `event`.
   - F3. The append-only rules act on UPDATE and DELETE statements only: `DETACH PARTITION`
     followed by `DROP TABLE` removes rows without any rule or the ORM guard seeing a DELETE.
   - F4. PostgreSQL (13 and later) accepts a `BEFORE DELETE … FOR EACH ROW` trigger on a
     partitioned table, so a delete can be refused loudly, or admitted only under a condition.
   - F5. Because `seq` restarts at 1 for every project, a seq-range partition never becomes
     cold: partition `[1, W)` keeps receiving the first W events of every new project.
   Evidence for F1–F4: if `psql` is on PATH and the test database answers, gather it and quote
   the output. The statements carry `$$`-quoted bodies and apostrophes, so they go in a file
   rather than on a command line: write this with `write_file` to the absolute path
   `STORM/scratch/adr114_evidence.sql` — a real
   directory outside every lane clone, so it can never reach `git status` — then run it with
   the single command below (autocommit; the errors are expected and are the evidence).
   Do not hand `write_file` a path containing `$TMPDIR`: it is a tool, not a shell, and would
   create a directory of that literal name inside the clone.
   ```sql
   CREATE SCHEMA adr114_scratch;
   SET search_path = adr114_scratch;
   SELECT version();
   CREATE TABLE t (p int, seq bigint) PARTITION BY RANGE (seq);
   CREATE TABLE t_default PARTITION OF t DEFAULT;
   INSERT INTO t VALUES (1, 5);
   CREATE TABLE t_1 PARTITION OF t FOR VALUES FROM (1) TO (10);
   CREATE TABLE t_10 PARTITION OF t FOR VALUES FROM (10) TO (20);
   INSERT INTO t VALUES (2, 15);
   ALTER TABLE t DETACH PARTITION t_10 CONCURRENTLY;
   CREATE RULE t_no_delete AS ON DELETE TO t DO INSTEAD NOTHING;
   ALTER TABLE t DETACH PARTITION t_10;
   DROP TABLE t_10;
   SELECT count(*) AS rows_left FROM t;
   DROP RULE t_no_delete ON t;
   CREATE FUNCTION refuse() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'refused'; END $$;
   CREATE TRIGGER t_guard BEFORE DELETE ON t FOR EACH ROW EXECUTE FUNCTION refuse();
   DELETE FROM t WHERE seq = 5;
   RESET search_path;
   DROP SCHEMA adr114_scratch CASCADE;
   ```
   ```
   psql "${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}" -f STORM/scratch/adr114_evidence.sql
   rm -f STORM/scratch/adr114_evidence.sql
   ```
   (Expected: the `t_1` create fails naming the default partition; the concurrent detach fails;
   the plain detach and drop succeed and `rows_left` is 1; the delete fails with `refused`.)
   If `psql` is missing or the database does not answer, state F1–F4 from PostgreSQL's
   documentation, mark each "unverified here", and list it under `## Verification owed`.
   Never leave the `adr114_scratch` schema behind.
4. `## Options considered` weighs at least these, each against every non-negotiable (append-only
   ledger; idempotent under replay; never block a worker on a human), the no-loss gate (R6 and a
   gapless `seq`), the ORM standard, sub-doctrines 7.a, 7.c, 8.g and 10 (fail loudly), and the
   disk goal of #114 — with consequences for each:
   - (A) **Raw forever; tiers are copies.** Nothing leaves `event`; sealed segments exist for
     export, the archive and survival (10.a); disk growth is bounded only by PostgreSQL's own
     TOAST compression. 
   - (B) **Detach and drop seq-range partitions** under today's key (F1, F2, F3, F5).
   - (C) **Re-key the partitions** as `LIST (project_id)` then `RANGE (seq)` per project, so a
     per-project window is a partition that can be detached once every row in it is sealed
     and verified; needs a 0013-style copy migration, partition DDL at project creation and
     ahead of each project's seq, and a written exemption for DDL that the rules cannot see.
   - (D) **A guarded tier move**: a migration replaces the `event_no_delete` rule with a
     `BEFORE DELETE` row trigger (F4) that raises unless an intact `ledger_segment` row covers
     that `(project_id, seq)`; the ORM guard admits exactly one statement shape for it; every
     other delete becomes loud instead of silent.
   - (E) Any further option you find, e.g. a periodic 0013-style table swap.
5. `## Decision` recommends one and states exactly:
   - the job kind name, its `EnqueueRequest` (`phase`, `idempotency_key` built with
     `domain/job.py:66-68` and a subject that makes a replay the same key, payload, priority,
     `max_attempts`), its lease entry in `_KIND_LEASES`, and who enqueues it and when (never a
     thread waiting on a human; it rides the job queue of ADR-0044, not a model loop's queue,
     since it is not model work — 8.c);
   - the steps of one run, in order, and why each step is replay-safe: read the raw rows
     outside the window of `TierConfig` (N ≥ 1 newest stay raw), seal them with the `jsonl+zlib`
     codec (`roadmap-114-tier-aware-reads-p1`), `put_segment` (a replayed seal is a no-op),
     verify by opening the stored segment and comparing, then — only if the chosen option
     removes raw rows — the removal, and what it ledgers;
   - how partitions are created ahead of `seq` under the chosen option, or why none are needed;
   - what happens to `TierManager`, `LedgerTierStoreInterface` and `InMemoryLedgerTierStore`
     (retire, or re-implement over `LedgerSegmentStore`);
   - which ledger events a rotation writes (new `EventKind` members, `domain/ledger.py:37`) and
     which measurements (8.g: bytes in, bytes out, ratio, duration, rows moved);
   - **if the recommended option removes a raw row from `event` by any means** (DELETE, DETACH,
     DROP), the Decision must be staged: what ships before the operator rules (the copy half),
     and what ships only after, with the ruling named under `## Open decisions for the operator`.
6. `## How each non-negotiable still holds` (required): one paragraph each for "never block a
   worker on a human", "the ledger is append-only", "every job is idempotent under replay",
   "the no-loss gate (R6, gapless seq)", "`domain/` stays pure", "everything configurable"
   (12.c: the window sizes are `[ledger]` keys), and "credits ≠ rate limit / capacity outranks
   completion" (say plainly whether rotation touches them).
7. Out of the ADR's scope, and said so: the codec, chunk size and content address
   (`roadmap-114-design-codec-chunking`), where the archive lives (#114 open question 4), the
   archival node's exchange protocol, encryption on the forge (#114 open question 1), the CLI.

## Where to change
- Create only the ADR draft above (Markdown, outside the clone). Run the `psql` block of item 3
  only against the test database, and drop the scratch schema.

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# Rotating the ledger through its storage tiers without breaking append-only` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:**` (the day you write it), and `**Cites:**` naming 7.c (`doctrines.md:82-91`), 7.a (`doctrines.md:72-78`), 8.c (`doctrines.md:196`), 8.g (`doctrines.md:316-324`), 9.b (`doctrines.md:349`), 10 (`doctrines.md:366-383`), 10.a (`doctrines.md:385-388`), 10.f (`doctrines.md:419`), 12.c (`doctrines.md:455`), ADR-0003, ADR-0004, ADR-0009, ADR-0044 and the non-negotiables it touches.
- [ ] `## Context` with at least 15 verified `path:line` anchors, including `migrations/0013_ledger_partitioning.sql:35`, `migrations/0013_ledger_partitioning.sql:65`, `migrations/0002_event.sql:30`, `src/vibey/domain/ledger_chain.py:20`, `src/vibey/infrastructure/ledger/tier_manager.py:68` and `src/vibey/domain/noloss.py:149`, and facts F1–F5 with their evidence or their "unverified here" mark.
- [ ] `## Options considered` with A–D (and any E), each with consequences against every item of Required behaviour 4.
- [ ] `## Decision` covering every point of Required behaviour 5.
- [ ] `## How each non-negotiable still holds` covering every point of Required behaviour 6.
- [ ] `## Consequences`.
- [ ] `## Lanes this unblocks`: a table with columns slug-to-be, title, one-line scope, files, sized for a 20B lane (one source file plus its interface, one test file) — including any migration (the next free number after 0016 at this cutoff, so 0017 or later) and its ORM change, the job kind, the handler, the `[ledger]` config keys (noting that their defaults wait on #114 open question 3), the `bootstrap.py` wiring, tier-aware search, and the fate of `TierManager`.
- [ ] `## Open decisions for the operator`: quote #114 open questions 2, 3 and 4 **verbatim** from `issue-audit/updates/114.md:159-164`, leave them unanswered, and add any ruling the Decision needs (for example: whether removing a raw row from `event` once an intact segment holds it is permitted under "The ledger is append-only. No updates, no deletes."), phrased as a question, unanswered.
- [ ] `## Verification owed` (the chaos-style test on real PostgreSQL under concurrent appends from #114's Acceptance, each unverified fact, the disk measurement).

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
Write this check with `write_file` to `STORM/scratch/adr114_check.py` — outside the clone, so it can
never show up in `git status` — then run it as one command and delete it:

```python
import re
from pathlib import Path
p = Path("STORM/specs/ADR-roadmap-114-rotation.md")
assert p.is_file(), "the ADR draft was not written"
text = p.read_text(encoding="utf-8")
flat = " ".join(text.split())
assert text.startswith("# Rotating the ledger through its storage tiers without breaking append-only"), "wrong title line"
required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context",
            "## Options considered", "## Decision", "## How each non-negotiable still holds",
            "## Consequences", "## Lanes this unblocks", "## Open decisions for the operator",
            "## Verification owed",
            "migrations/0013_ledger_partitioning.sql:35", "migrations/0013_ledger_partitioning.sql:65",
            "migrations/0002_event.sql:30", "src/vibey/domain/ledger_chain.py:20",
            "src/vibey/infrastructure/ledger/tier_manager.py:68", "src/vibey/domain/noloss.py:149",
            "doctrines.md:82", "doctrines.md:455", "ADR-0044", "F1", "F2", "F3", "F4", "F5"]
missing = [h for h in required if h not in text]
assert not missing, f"missing: {missing}"
quotes = [
    "is declarative partitioning inside one PostgreSQL enough, or is multi-node sharding (several database servers) in scope?",
    "Set by measurement (8.g) on this repository's ledgers, or fixed by you?",
    "the blob surface (Garage, 8.b), the forge (per the comment), or both?",
]
unquoted = [q for q in quotes if q not in flat]
assert not unquoted, f"open questions not quoted verbatim: {unquoted}"
anchors = set(re.findall(r"[\w./-]+\.(?:py|sql|toml|md|yml):\d+", text))
assert len(anchors) >= 15, f"only {len(anchors)} distinct path:line anchors"
for word in ("TBD", "lorem", "TODO"):
    assert word not in text, f"placeholder {word!r} left in the draft"
print("ADR draft complete")
```

    python3 "STORM/scratch/adr114_check.py"   # prints: ADR draft complete
    rm -f "STORM/scratch/adr114_check.py"
    # The scratch schema of Required behaviour 3 must be gone:
    psql "${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}" -tAc "SELECT count(*) FROM pg_namespace WHERE nspname = 'adr114_scratch'" 2>/dev/null || true   # prints 0 (or nothing without psql)
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- Any code, migration or test; the codec and chunking design; the archive's location and the
  archival node; encryption; the CLI; the benchmark table.
- The tree's `docs/` and ADR directories. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
