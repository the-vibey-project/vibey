## Title
docs(adr): draft the forge-state ledger design (#136 S4): where sealed forge records live, how they are written once, redacted and tiered

## Why
Issue #136 (rewrite: `issue-audit/updates/136.md`, "Proposed child issues" 6) marks S4
"Design needed first": decide between a separate `forge_record` table and forge `EventKind`s in
`event`; the migration; the redaction policy (7.c); the tier placement (#114); then a writer in
`src/vibey/infrastructure/` behind an application port, with an in-memory fake, through the ORM
seam. The gap, verified at integration `4317cff6`:
- The snapshot writes files only: "writes nothing into the vibey ledger: that writer needs the
  storage tiers of vibey#114" (`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:17-21`). The sink
  seam already exists as `SnapshotStoreInterface`
  (`src/vibey_tools/gh/vibey_gh/interfaces/forge_snapshot_interface.py:130-167`), and the
  interface module says "the vibey ledger writer is a second store" (`:11-12`).
- `event` is per project: `project_id uuid NOT NULL REFERENCES project(id)`, a gapless per-project
  `seq`, `phase` and `correlation_id NOT NULL` (`migrations/0013_ledger_partitioning.sql:18-35`,
  `append_event` at `:84-116`). A forge record belongs to a repository, not to a delivery project.
- Ledger redaction rewrites a payload before its digest (`src/vibey/infrastructure/db/ledger_repository.py:103-109`)
  and records nothing about what it removed (`src/vibey/infrastructure/ledger/redact.py:56-60`),
  while a forge record is sealed over its payload in vibey-gh, so rewriting it later breaks its seal.

Ratified law the ADR must honour: 7.c, record everything, append-only, redactions recorded
(`src/vibey_tools/gh/docs/doctrines.md:82-91`); 7.a, searchable by anyone
(`doctrines.md:72-78`); 8.b, the sovereign host holds a declared relay's state
(`doctrines.md:179-186`); 9.b (`doctrines.md:349`); 10.e (`doctrines.md:417`); 10.f
(`doctrines.md:419`); 12.c (`doctrines.md:455`); SD-01 §1 and §7
(`src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md:26`, `:73`). The operator's
standards: ORM behind interfaces (storm draft `specs/ADR-orm.md` §1, §5, §6), a registered
in-memory fake for every new port (`specs/ADR-test-harness-fakes-amendment.md`), vibey-gh stays
stdlib-only (`src/vibey_tools/gh/pyproject.toml:30`), new migrations take the next free number
(0014 is `rmq-r08`'s, 0015 is ADR-0047's, so **0016 at this cutoff**).

## Required behaviour
The lane writes exactly one file, the draft ADR at the absolute path
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-136-forge-ledger.md`, with
`write_file`. It changes no file in its clone and commits nothing.

Before writing, read every file:line listed below in the integration clone (your working
directory) and cite only lines you read. Where a line number has moved, cite where the text
is now. Evidence to read and cite:
- vibey-gh: `vibey_gh/forge_snapshot.py:17-21` (files only), `:380-417` (`append`: a record is
  written only when its payload digest differs from the latest for that native object, the
  idempotence the file store already has), `:396-408` (the envelope fields), `:429-496` (the
  chain is re-checked on load); `vibey_gh/interfaces/forge_snapshot_interface.py:130-167`
  (`SnapshotStoreInterface`: `manifest`, `chain`, `append`, `write_manifest`);
  `docs/forge-snapshot.md:201-203` (point in time: "its latest record with a `captured_at` at or
  before that moment") and `:205-211` (the canonical form is the ledger's);
  `test/test_forge_snapshot.py:542-546` (the canonical form matches `vibey.domain.ledger` byte
  for byte); `pyproject.toml:30` (`dependencies = []`).
- vibey: `src/vibey/domain/ledger.py:37-70` (`EventKind`, a closed vocabulary; writers are
  strict, `:6-13`), `:209-214` (`canonical_bytes`, `digest_event`);
  `migrations/0013_ledger_partitioning.sql:18-35`, `:37-41` (one DEFAULT partition),
  `:65-66` (append-only rules), `:84-116` (`append_event`);
  `src/vibey/infrastructure/db/ledger_repository.py:103-109`;
  `src/vibey/infrastructure/ledger/redact.py:15` (`REDACTED`), `:56-60`;
  `src/vibey/infrastructure/db/interfaces/orm_interface.py:14` (`PostgresOrmInterface`),
  `src/vibey/infrastructure/db/orm.py:32`, `src/vibey/infrastructure/db/orm_models.py:678`
  (`ORM_TABLE_MODELS`); `src/vibey/domain/ledger_tier.py:8-16` (`TierConfig`),
  `src/vibey/infrastructure/ledger/tier_manager.py:48` (`reconcile_tiers(project_id, …)`, per
  project); `src/vibey/application/interfaces/ledger.py:149-161` (`LedgerShardStore`, the
  published shard), `src/vibey/infrastructure/ledger/static_export.py:199`;
  `src/vibey/cli/main.py:86-90` (`vibey ledger search|export|site`);
  `tests/fakes/test_port_parity.py:25-30` (the port table).
- The two issue rewrites `/private/tmp/claude-501/storm/qwenstorm-3.0.0/issue-audit/updates/136.md`
  and `…/114.md`; the storm drafts `…/specs/ADR-orm.md` and
  `…/specs/ADR-test-harness-fakes-amendment.md`; and the capture specs
  `…/specs/roadmap-136-capture-repo-metadata.md` (declared `redact` paths, the `[REDACTED]`
  marker kept in the record) and `…/specs/roadmap-145-capture-workflow-runs.md` (the `hold`).

The ADR carries these parts, in this order, each heading exactly as written:
1. First line: `# The forge-state ledger: sealed forge records in their own append-only table, written once per seal`
   (no number). Then one line holding `**Status:** proposed`, `**Date:**` (the day you write
   it), and `**Cites:**` naming 7.c, 7.a, 8.b, 9.b, 10.e, 10.f, 12.c and SD-01 with their
   `doctrines.md:<line>` anchors above, ADR-0002, ADR-0003, ADR-0016, ADR-0017 (in
   `docs/architecture/decisions/`), and the storm drafts `ADR-orm.md` and
   `ADR-test-harness-fakes-amendment.md`.
2. `## Context` — what exists and what is missing, each fact with its file:line: the file
   store and its seam; `event`'s per-project shape; redaction before digest with no record of
   it; the tier manager keyed by project; the published shard (7.a).
3. `## Options considered` — at least these two, each with its consequences:
   - **A. A separate `forge_record` table.** Rows are the sealed records unchanged; the
     record's `sha256` is unique, so writing the same record twice is a no-op; scoped by
     `(forge, repository, class)`; `prev` keeps each class's chain; no `project_id`, `phase` or
     `seq` is invented.
   - **B. Forge `EventKind`s in `event`.** One ledger for search and R6 digests, but every row
     needs a `project_id`, `phase` and `correlation_id` a repository does not have; forge volume
     interleaves with a project's gapless `seq`; the ledger's redaction rewrites the sealed
     payload and breaks its seal; and `event_digest` is not unique, so idempotence needs a
     second mechanism.
   A third option may be added (for example, files only, indexed by the ledger).
4. `## Decision` — recommend option A, argued from the evidence, unless something you read
   contradicts it; then keep A and record the contradiction under `## Verification owed`.
5. `## The migration` — `migrations/0016_forge_record.sql` ("the next free number; 0016 at
   this cutoff"): a `forge_record` table (every envelope field, `payload jsonb`,
   `sha256 text PRIMARY KEY`, `prev text`, an index on
   `(forge, repository, class, native_id, captured_at)` for point-in-time reads), a
   `forge_capture` table holding each capture's manifest (append-only too), the same
   `DO INSTEAD NOTHING` rules as `event` (`0013:65-66`), and range partitioning with one DEFAULT
   partition as `0013:37-41` does, so #114's rotation can adopt it without moving rows by hand.
   Forward-only and checksummed (ADR-orm §6).
6. `## The idempotent writer` — an application port (named, for example
   `ForgeRecordSink` in `src/vibey/application/interfaces/forge_records.py`) with an in-memory
   fake registered in the port table (`tests/fakes/test_port_parity.py:25-30`, the registry of
   lane `fakes-registry`); the PostgreSQL implementation in `src/vibey/infrastructure/db/`
   through `PostgresOrmInterface.transaction()` with
   `pg_insert(...).on_conflict_do_nothing(index_elements=[sha256])` (the pattern of
   `specs/orm-job-statements-enqueue.md`), never raw SQL; the forge tables registered in
   `ORM_TABLE_MODELS` (`orm_models.py:678`) and covered by the append-only guard (ADR-orm §5).
   State the property: the same record digest is written once, so a replayed capture writes
   nothing new (CLAUDE.md "Every job is idempotent under replay").
7. `## The vibey-gh sink` — vibey-gh keeps `dependencies = []` and gains nothing: the ledger
   store is a second implementation of its existing `SnapshotStoreInterface`, living in
   `src/vibey/infrastructure/` (vibey may import the dependency-free vibey-gh), which delegates
   to the port. The file store stays; a capture can write both.
8. `## Redaction (7.c)` — redaction happens before sealing, in the capture, so a record's seal
   verifies in the file and in the ledger alike: vibey-gh declares per-class `redact` paths
   (the mechanism of `roadmap-136-capture-repo-metadata`) and, when vibey runs the capture into
   the ledger, it injects vibey's own redactor (`redact.py:56-60`) through a new vibey-gh seam
   (a redactor interface, stdlib-only), so free-text credentials are caught too. Every
   redaction stays visible as `[REDACTED]` (`redact.py:15`) and the manifest counts redactions
   per class, so none is silent. People's private details follow SD-01 §1.
9. `## Tier placement (#114)` — `forge_record` is its own tiered relation, not part of `event`'s
   per-project tiers (`tier_manager.py:48` is keyed by project); S4 lands on the DEFAULT
   partition and does not wait for #114; #114's rotation lane extends to `forge_record` by
   range on `captured_at`. Say which #114 child owns that.
10. `## Consequences` — what gets easier, what gets harder, what stays unanswered.
11. `## Lanes this unblocks` — a table whose header row is exactly
    `| Slug-to-be | Title | Scope | Size |`, one row per lane, each sized for one 20B lane
    (one source file plus its interface, and one test file). At least these rows:
    `roadmap-136-ledger-forge-migration`, `roadmap-136-ledger-forge-models`,
    `roadmap-136-ledger-forge-port`, `roadmap-136-ledger-forge-writer`,
    `roadmap-136-ledger-forge-store`, `roadmap-136-gh-redactor-seam`,
    `roadmap-136-ledger-forge-capture-cli`, and `roadmap-136-ledger-forge-state-as-of` whose
    title names `vibey ledger forge-state --as-of MOMENT` (point-in-time reconstruction: the
    latest record per native object with `captured_at` at or before the moment,
    `docs/forge-snapshot.md:201-203`).
12. `## Open decisions for the operator` — quote #136's open question 3 verbatim, exactly:
    > **Public or private?** Captured comments include people's text. The public ledger shard
    > (7.a) needs a policy for what is published versus kept in a private tier.

    The ADR does NOT answer it. Say only what the design does until it is answered: forge
    records are held in the database and are not added to the published shard
    (`LedgerShardStore`, `application/interfaces/ledger.py:149-161`), because SD-01 §7 says
    "Silence from the operator means no"
    (`src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md:73`).
13. `## Verification owed` — what must be proven by the lanes and by whom: the seal verifying
    after a ledger round trip; a replayed capture writing nothing; the migration applying on
    PostgreSQL 17 (integration tier); the canonical form test staying green.

## Where to change
- Create only `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-136-forge-ledger.md`
  (outside the clone). Its first line is the title above; ADR drafts carry no provenance header.
- No file in the clone changes. Nothing is committed.

## Acceptance criteria
The ADR's required sections, each checked by the script below:
- [ ] A number-less `# ` title line; `**Status:** proposed`, `**Date:**`, `**Cites:**`.
- [ ] `## Context`, `## Options considered`, `## Decision`, `## The migration`,
      `## The idempotent writer`, `## The vibey-gh sink`, `## Redaction (7.c)`,
      `## Tier placement (#114)`, `## Consequences`, `## Lanes this unblocks`,
      `## Open decisions for the operator`, `## Verification owed`, in that order.
- [ ] The migration is named `0016_forge_record.sql`.
- [ ] The lanes table has the exact header row and at least 8 rows, one naming
      `vibey ledger forge-state --as-of`.
- [ ] #136's open question 3 is quoted verbatim under `## Open decisions for the operator`.
- [ ] At least 20 lines cite a `file:line` anchor.
- [ ] `git status --porcelain` in the clone is empty.

## Tests to write first (TDD)
None in the clone. The check script below is the test; write the ADR until it passes.

## Checks the lane must run (all must pass)
```bash
python3 -c '
from pathlib import Path
adr = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-136-forge-ledger.md")
assert adr.is_file(), "the ADR file does not exist"
text = adr.read_text(encoding="utf-8")
lines = text.splitlines()
assert lines[0].startswith("# ") and not lines[0][2:3].isdigit(), "first line is a number-less title"
for needle in ("**Status:** proposed", "**Date:**", "**Cites:**", "0016_forge_record.sql"):
    assert needle in text, "missing " + needle
headings = ["## Context", "## Options considered", "## Decision", "## The migration",
    "## The idempotent writer", "## The vibey-gh sink", "## Redaction (7.c)",
    "## Tier placement (#114)", "## Consequences", "## Lanes this unblocks",
    "## Open decisions for the operator", "## Verification owed"]
positions = []
for heading in headings:
    assert heading in lines, "missing heading " + heading
    positions.append(lines.index(heading))
assert positions == sorted(positions), "headings out of order"
lanes = text.split("## Lanes this unblocks", 1)[1].split("## Open decisions for the operator", 1)[0]
assert "| Slug-to-be | Title | Scope | Size |" in lanes.splitlines(), "lanes table header"
rows = [row for row in lanes.splitlines() if row.startswith("| roadmap-")]
assert len(rows) >= 8, "at least 8 lane rows"
assert "vibey ledger forge-state --as-of" in lanes, "the point-in-time lane"
opens = text.split("## Open decisions for the operator", 1)[1].split("## Verification owed", 1)[0]
flat = " ".join(line.lstrip("> ").strip() for line in opens.splitlines())
question = "**Public or private?** Captured comments include people\x27s text. The public ledger shard (7.a) needs a policy for what is published versus kept in a private tier."
assert question in flat, "#136 question 3 is not quoted verbatim"
print("ADR structure OK")
'
test "$(grep -cE '[A-Za-z0-9_./-]+\.(py|sql|md|toml):[0-9]+' /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-136-forge-ledger.md)" -ge 20
test -z "$(git status --porcelain)"
```

## Out of scope
- Implementing any lane the ADR names; S5 restore (blocked on #136 open question 2); security
  alerts (blocked on #145 open question 4); Forgejo capture parity (after the gaps.md §L8 lane).
- Answering #136 open question 3.
- Any file in the clone: code, `docs/`, ADRs under `docs/architecture/decisions/`, CHANGELOG.
- Do not push, do not commit.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
