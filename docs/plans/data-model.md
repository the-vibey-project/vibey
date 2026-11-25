---
description: "vibey's PostgreSQL schema as the 23 migrations build it: the projects, the job queue, the partitioned append-only ledger, gates, handoffs, engine health and the newer state-sync, triage and ACP tables."
---

# The data model: vibey's PostgreSQL schema, table by table

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** everything vibey must not forget lives in one PostgreSQL
> database (14 to 18), built by 23 forward-only migrations shipped inside the package. The
> job queue uses `FOR UPDATE SKIP LOCKED`; the ledger (`event`) is range-partitioned on `seq`
> with primary key `(project_id, seq)`, and triggers refuse every `UPDATE`, `DELETE` and
> `TRUNCATE`. Read this page before you write SQL or a migration against vibey's tables.

> **How current this page is.** Checked on 2026-11-24 against the migrations in
> `src/vibey/infrastructure/db/migrations/` (0001–0023, the full set on `develop` at
> `d91a3791e`, vibey-engine 0.4.0) and the repositories beside them. This revision corrects
> the ledger's shape (§3.2 now shows the partitioned table of 0013 and the triggers of
> 0016/0017 instead of the rules they replaced), adds `triaged_ticket` (0020) and the
> `vibey_ledger_appended` notification (0019), says which tables have no ORM object, and
> fixes the foreign-key and retention claims. Sections that described tables with no
> migration (visual revisions, deployment contracts), a transition advisory lock and
> pruning are kept as designs and marked **proposed** or **planned**. Several provisioned
> tables (`work_item`, `open_item`, `artifact`, `budget_ledger`) exist in the schema but no
> repository reads or writes them yet (§3). This page lives under `docs/plans/`, which the
> published site leaves out on purpose; it is kept current because the agent instruction
> files point here.

## The idea, in one conversation

> The library was nearly empty. Daniel had a migration file open and was counting the
> `CREATE` statements on his fingers.
>
> **Daniel:** Professor, why is the ledger split into partitions? It is one list of events.
>
> **Professor Feynman:** Think of a library's day books. One enormous book is fine until it
> is too heavy to lift. So you keep one shelf of volumes, each holding a run of page numbers.
> The catalogue still says "page 1,478 of project seven", and you go to the right volume.
>
> **Daniel:** And the page number is `seq`?
>
> **Professor Feynman:** Yes: one gapless count per project, which is why the key is
> `(project_id, seq)` and not the event's own id. Two projects can both have a page 12.
>
> **Daniel:** What stops someone rubbing a page out?
>
> **Professor Feynman:** At first, a polite notice saying "please do not erase", which a
> determined person could ignore and the librarian could take down. Since migration 0016 it
> is a guard on every volume who refuses out loud, and the clerks are given pens that cannot
> erase at all: the application's database role may only read and add. The picture stops in
> one place: today every page still sits in a single default volume. The shelf is built; it
> has not needed a second volume yet.

## See it on your machine

1. Apply the migrations, as the schema's owner.

   ```bash
   vibey migrate
   ```

   It reads the owner's DSN from `VIBEY_PG_MIGRATE_URL` and the application's from
   `VIBEY_PG_URL`, so set both first. It applies every migration not yet recorded in
   `schema_migration`, grants the application role exactly its declared privileges, then
   connects as that role and reports whether the ledger guard is in force. It exits 1 when
   the guard is not in force, for example when both DSNs name the same role.

2. List the guards on the ledger, read-only.

   ```bash
   psql "$VIBEY_PG_URL" -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'event'::regclass AND NOT tgisinternal ORDER BY tgname;"
   ```

   You should see three rows: `event_announce_append` (0019), `event_append_only` and
   `event_no_truncate` (0016). Do not test the guard by trying to rewrite a real ledger.

## Daniel's teach-back

> **Daniel:** vibey keeps everything in one PostgreSQL database, built by 23 migrations that
> only ever move forward. Jobs wait in the `job` table and workers take them with `SKIP
> LOCKED`. The ledger is the `event` table, numbered by a gapless `seq` per project and keyed
> on `(project_id, seq)`, partitioned by `seq`, and guarded by triggers so no one can change
> or delete a row. Corrections are new events.
>
> **Professor Feynman:** Right. One fix: "no one" means no SQL statement. The owner role could
> still disable a trigger, which is why vibey's own processes never connect as the owner.

> PostgreSQL 14+. CI exercises majors 14–18; the chart default is PostgreSQL 17.
> All timestamps `timestamptz`. All ids `uuid` except `event.seq`
> (gapless bigint per project) and human-facing item ids (short prefixed strings).
> Migrations are forward-only. They run as the schema's owner: `vibey migrate` (the only
> reader of `VIBEY_PG_MIGRATE_URL`), or `build_app()` (`src/vibey/bootstrap.py`) when the
> application's own role may migrate (a single-DSN install); see §7 and ADR-0055.

The live schema also has a Pydantic-backed SQLAlchemy projection in
`src/vibey/infrastructure/db/orm_models.py`. It uses SQLModel and declares 14 table
models: 13 of the tables in §3 plus `schema_migration` (§7). Four later tables have **no**
ORM object: `triaged_ticket` (0020, read and written by `scripts/triage_queue.py`),
`state_sync` (0022, `infrastructure/state/postgres_state_store.py`), `acp_session` and
`acp_session_event` (0023, `infrastructure/db/acp_session_repository.py`).
`PostgresOrm` provides async sessions. Migrations remain authoritative and the
projection deliberately does not call `metadata.create_all()`. The existing
asyncpg repositories continue to own operations whose correctness depends on
PostgreSQL-specific locking, append-only rules, or transactional `NOTIFY`.

---

## 1. Why PostgreSQL

Recorded fully in [ADR-0002](../architecture/decisions/0002-postgres-not-sqlite.md).
The short version:

| Requirement | SQLite | PostgreSQL |
|---|---|---|
| N workers claiming jobs concurrently | no row locks, **no `SKIP LOCKED`** | `FOR UPDATE SKIP LOCKED` |
| Crash-safe leases | mark-then-return leaks locked rows forever | lease + expiry + reaper |
| Worker wakeup without polling | poll only | `LISTEN` / `NOTIFY` |
| Ledger payload queries | `json1`, no real index | `jsonb` + GIN |
| Phase-transition mutual exclusion | file lock | row-level compare-and-set (`UPDATE … WHERE phase = $expected`) |
| Shared integration branch | file lock | session advisory lock (`pg_try_advisory_lock`, ADR-0029) |

WAL mode fixes reader/writer blocking; vibey's contention is writer/writer.

---

## 2. Entity relationships

```mermaid
erDiagram
    project ||--o{ cycle_record : has
    project ||--o{ job : has
    project ||--o{ event : has
    project ||--|| event_seq : sequences
    project ||--o{ engine_health : tracks
    project ||--o{ rotation_cursor : rotates
    job ||--o{ job_dependency : "depends on"
    job ||--o{ human_gate : raises
    job ||--o{ handoff : triggers
    event ||--o{ open_item : projects
    project ||--o{ work_item : has
    work_item ||--o{ job : "implemented by"
    project ||--o{ artifact : produces
    project ||--o{ budget_ledger : spends
    handoff }o--|| engine_health : from
    handoff }o--|| engine_health : to
    project |o--o{ triaged_ticket : "dispatched as"
    acp_session ||--o{ acp_session_event : records
```

`state_sync` (0022) stands alone: one row per sync remote, keyed by `remote`, with no
foreign key.

Of the tables of 0001–0011, every one except `project` and `job_dependency` carries a
declared foreign key to `project`; `job_dependency` references `job` twice,
`handoff.job_id` and `human_gate.job_id` reference `job`, and
`open_item.superseded_by` references `open_item`. The later tables differ:
`triaged_ticket.project_id` is nullable and `ON DELETE SET NULL` (a ticket exists before
its project), `acp_session_event` references `acp_session`, and `state_sync` and
`acp_session` reference nothing. The `work_item → job`, `event → open_item` and
`handoff → engine_health` edges are logical (text ids), not constraints.
`cycle_record` is a conceptual grouping by `(project_id, cycle)`; there is no
such table. `handoff.job_id` is always written as `NULL` today
(`PostgresHandoffRepository.record`).

---

## 3. Core tables

Every `CREATE` below is from a file in `src/vibey/infrastructure/db/migrations/`. Tables `work_item` (0004),
`open_item` (0005), `artifact` and `budget_ledger` (0008) are created and asserted
present by `tests/infrastructure/db/test_migrator.py`, but no repository in
`src/vibey` reads or writes them yet: their state currently lives in the ledger
(`event`), in in-memory projections (`domain/projections.py`), and in `.vibey/`
files.

### 3.1 `project`

```sql
-- 0001_project.sql
CREATE TYPE phase AS ENUM (
    'intake','design','build','review','deploy','done','abandoned'
);

CREATE TABLE project (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    repo_path       text NOT NULL,
    phase           phase NOT NULL DEFAULT 'intake',
    cycle           integer NOT NULL DEFAULT 1,
    max_cycles      integer NOT NULL DEFAULT 10,
    config          jsonb NOT NULL,           -- the resolved vibey.toml
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT project_cycle_bounded CHECK (cycle >= 1 AND cycle <= max_cycles + 1)
);

CREATE UNIQUE INDEX project_repo_uniq ON project (repo_path);   -- replaced by 0021 (below)

-- 0010_visual_design_phase.sql
ALTER TYPE phase ADD VALUE IF NOT EXISTS 'visual_design' AFTER 'design';

-- 0011_deployment_stage_set_phases.sql
ALTER TYPE phase ADD VALUE IF NOT EXISTS 'deploy_design' BEFORE 'deploy';
ALTER TYPE phase ADD VALUE IF NOT EXISTS 'deploy_execute' BEFORE 'deploy';
ALTER TYPE phase ADD VALUE IF NOT EXISTS 'deploy_review' BEFORE 'deploy';

-- resulting enum order: intake, design, visual_design, build, review,
--   deploy_design, deploy_execute, deploy_review, deploy, done, abandoned

-- 0021_project_repo_live_uniq.sql
DROP INDEX project_repo_uniq;
CREATE UNIQUE INDEX project_repo_live_uniq ON project (repo_path) WHERE phase <> 'abandoned';
```

**One live project per checkout.** `project_repo_live_uniq` keeps two live projects out
of one checkout: every phase but `abandoned` holds its `repo_path`, `done` included. 0001's
index covered every row, so an abandoned project held its checkout for ever and nothing
could start there again (live on #963); 0021 narrows it to the live rows. `abandoned` is
terminal, so an abandoned row can never become live and collide. Any number of abandoned
projects may share a path with at most one live one, and every reader goes by project id,
so the abandoned rows stay readable. `PostgresProjectRepository.create` stores the
resolved path and turns a refusal by this index -- and only this one -- into
`CheckoutHeld`, naming the live holder's id and phase; `vibey new` prints it as one
`Error:` line and exits 3. The ORM declares the same partial index (`ProjectOrm`).

Migrations 0010 (M5) and 0011 (M10) only widen the enum. The legacy `deploy` value
is never removed (PostgreSQL cannot drop an enum value) and no project rows are
rewritten. `Phase.DEPLOY` survives in `domain/phase.py` as a runtime bridge:
`ReviewDeploymentChoiceHandler` moves an opted-in project `review → deploy` and
enqueues `deploy.design`; `DeployDesignBridgeHandler` then moves it
`deploy → deploy_design` and enqueues `deploy.interview`, so target scope and
consent are re-established in phase ④ (ADR-0013, ADR-0014).

There is no persisted `completion_mode` column. The local-versus-deployed outcome
is carried in `TransitionEvidence.completion_mode` (`domain/phase.py`) and in the
handler's result payload; the durable record is the `DeploymentOptedIn` or
`DeploymentDeclined` ledger event, not a column on `project`.

### 3.1.1 Visual design state (file-backed; tables proposed)

The VISUAL_DESIGN interstitial persists no rows today. `FileVisualInventoryRepository`
(`src/vibey/infrastructure/db/visual_inventory_repository.py`) writes the screen
inventory, including each surface's media manifest (`asset_key`, `modality`,
`prompt`), to `<repo>/.vibey/runs/<cycle>/visual/inventory.json`, and `publish`
renders the context artifacts into `<repo>/.vibey/context/visual/`. Acceptance and
waiver are appended to the ledger as `VisualDesignAccepted` / `VisualDesignWaived`
(`application/visual_acceptance.py`). The DESIGN-side choice is appended as
`VisualDesignOptedIn` / `VisualDesignDeclined` by `DesignAcceptanceService`
(`application/design_acceptance.py`, from `vibey design accept --visual/--no-visual`)
before the phase transitions.

**Proposed, no migration.** The design calls for Postgres tables so generated
assets are immutable revisions with provenance and cost:

```sql
-- PROPOSED -- not in migrations/
CREATE TYPE media_modality AS ENUM ('image','audio','video');
CREATE TYPE visual_asset_decision AS ENUM ('pending','accepted','rejected','supplied','waived');

CREATE TABLE visual_revision (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle               integer NOT NULL,
    revision            integer NOT NULL,
    opt_in_event_id     uuid NOT NULL,
    inventory           jsonb NOT NULL,
    design_system       jsonb NOT NULL,
    accepted_at         timestamptz,
    UNIQUE (project_id, cycle, revision)
);

CREATE TABLE visual_asset (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    visual_revision_id  uuid NOT NULL REFERENCES visual_revision(id) ON DELETE CASCADE,
    asset_key           text NOT NULL,
    screen_id           text NOT NULL,
    state               text NOT NULL,
    modality            media_modality NOT NULL,
    prompt              text NOT NULL,
    prompt_digest       text NOT NULL,
    provider_id         text,
    model_version       text,
    request_id          text,
    artifact_digest     text,
    artifact_uri        text,
    moderation          jsonb NOT NULL DEFAULT '{}',
    rights_metadata     jsonb NOT NULL DEFAULT '{}',
    retention_policy    text,
    cost_usd            numeric(12,6) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0),
    decision            visual_asset_decision NOT NULL DEFAULT 'pending',
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (visual_revision_id, asset_key, prompt_digest)
);

CREATE TABLE media_provider_cursor (
    project_id          uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    modality            media_modality NOT NULL,
    cursor              bigint NOT NULL DEFAULT 0 CHECK (cursor >= 0),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, modality)
);
```

Under that proposal the prompt is retained for reproducibility, secrets and
sensitive source content are redacted before persistence, and regeneration
creates a new `visual_asset` row rather than mutating accepted evidence.

### 3.1.2 Deployment state (file-backed; tables proposed)

Phases ④–⑥ persist no rows today. `FileDeploymentStateRepository`
(`src/vibey/infrastructure/deploy/state_repository.py`) writes the accepted
`DeploymentSpec` to `<repo>/.vibey/deploy/spec.json` and the `DeploymentConsent`
to `<repo>/.vibey/deploy/consent.json`. The REVIEW opt-in and decline are appended
as `DeploymentOptedIn` / `DeploymentDeclined`
(`application/review_deployment_choice_handler.py`), the accepted deployment spec as
a `DecisionRecorded`, and execution evidence as `ArtifactProduced` (success) or
`FindingRaised` (failure) events (`application/deploy_execute_handler.py`).

**Proposed, no migration.** The design calls for contract and attempt tables that
bind each attempt to the accepting and consenting ledger events:

```sql
-- PROPOSED -- not in migrations/
CREATE TYPE deployment_outcome AS ENUM (
    'running','verified_success','input_required','cancelled'
);

CREATE TABLE deployment_contract (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle               integer NOT NULL,
    revision            integer NOT NULL,
    target_scope_digest text NOT NULL,
    spec                jsonb NOT NULL, -- no secret values; references only
    accepted_event_id   uuid NOT NULL,
    consent_event_id    uuid NOT NULL,
    accepted_at         timestamptz NOT NULL,
    superseded_at       timestamptz,
    UNIQUE (project_id, cycle, revision)
);

CREATE TABLE deployment_attempt (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id           uuid NOT NULL REFERENCES deployment_contract(id),
    attempt               integer NOT NULL CHECK (attempt >= 1),
    outcome               deployment_outcome NOT NULL DEFAULT 'running',
    azure_operation_ids   text[] NOT NULL DEFAULT '{}',
    resource_ids          text[] NOT NULL DEFAULT '{}',
    artifact_digest       text NOT NULL,
    cost_usd              numeric(12,6) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0),
    started_at            timestamptz NOT NULL DEFAULT now(),
    completed_at          timestamptz,
    evidence              jsonb NOT NULL DEFAULT '{}',
    UNIQUE (contract_id, attempt)
);
```

Under that proposal, retrying an unchanged contract creates another attempt, and
changing scope creates a new contract revision that invalidates the previous
consent.

### 3.2 `event` — the ledger

The table as it stands after migration 0013, which rebuilt the 0002 table as a
range-partitioned one (copying every row and refusing to finish if the count changed):

```sql
-- 0002_event.sql
CREATE TYPE provenance AS ENUM ('trusted','agent','untrusted');

-- 0013_ledger_partitioning.sql (the table vibey runs on today)
CREATE TABLE event (
    event_id        uuid NOT NULL DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    seq             bigint NOT NULL,
    cycle           integer NOT NULL,
    phase           phase NOT NULL,
    kind            text NOT NULL,
    engine_id       text,                     -- NULL for vibey-authored events
    job_id          uuid,
    causation_id    uuid,
    correlation_id  uuid NOT NULL,
    provenance      provenance NOT NULL DEFAULT 'agent',
    produced_at     timestamptz NOT NULL DEFAULT now(),
    payload         jsonb NOT NULL,
    digest          text NOT NULL,            -- sha256 of canonical payload
    CONSTRAINT event_seq_uniq PRIMARY KEY (project_id, seq),
    CONSTRAINT event_id_seq_uniq UNIQUE (event_id, seq)
) PARTITION BY RANGE (seq);

CREATE TABLE event_partitioned_0013_default PARTITION OF event DEFAULT;

CREATE INDEX event_project_seq   ON event (project_id, seq);
CREATE INDEX event_kind          ON event (project_id, kind, seq);
CREATE INDEX event_correlation   ON event (correlation_id, seq);
CREATE INDEX event_payload_gin   ON event USING gin (payload jsonb_path_ops);
-- (0013 also recreates 0012's three search indexes on the new table; see below)

-- Append-only: no UPDATE, no DELETE, no TRUNCATE -- by the database (0016, ADR-0055).
CREATE TRIGGER event_append_only BEFORE UPDATE OR DELETE ON event
    FOR EACH ROW EXECUTE FUNCTION ledger_refuse_rewrite();
CREATE TRIGGER event_no_truncate BEFORE TRUNCATE ON event
    FOR EACH STATEMENT EXECUTE FUNCTION ledger_refuse_rewrite();
```

**What changed in 0013.** Before it, `event_id` was the primary key and
`(project_id, seq)` a unique constraint. Since it, the primary key is `(project_id, seq)`
(still named `event_seq_uniq`) and `event_id` is unique only together with `seq`, because
a unique constraint on a partitioned table must include the partition key. Address one
event by `(project_id, seq)`; an `event_id` lookup is still possible but is not a key on
its own. Every row lives in the one default partition today; range partitions can be
attached later without another rewrite. 0013 also re-created the 11-argument
`append_event()` against the new table; the `event_seq` counters were left untouched, so
every project's next number carried over.

A rewrite is refused out loud: `the ledger is append-only: UPDATE on event is refused`,
SQLSTATE `42501`, for every role, the owner included.

- **Partitions.** The row trigger is cloned onto every partition, present and future.
  `ledger_guard_partitions()` attaches the `TRUNCATE` guard, which PostgreSQL does not
  clone, on every migration run.
- **The earlier rules.** Migrations 0002 and 0013 used `DO INSTEAD NOTHING` rules, which
  made a stray write a silent no-op. They did not fire for a statement addressed to a
  partition or for `TRUNCATE`, and the owner (whom the worker connected as) could disable
  them. 0016 drops them.
- **The application role.** It holds `SELECT` and `INSERT` on `event` and nothing more
  (`APP_ROLE_GRANTS`), so it cannot disable a trigger either. See
  [the configuration reference](../reference/configuration.md#database-roles).

**History: what the rules did not stop.** Checked against the migrated schema on
2026-09-24, before 0016, as the role vibey then connected with (the table's owner): an
`UPDATE` or `DELETE` addressed to a partition (`event_partitioned_0013_default`) rather
than to `event` changed rows, because a rule on a partitioned parent does not fire for its
partitions; `TRUNCATE event` emptied the ledger, because rules never fire on `TRUNCATE`; and
the owner could `ALTER TABLE event DISABLE RULE` or drop the rules outright. Migrations 0016
and 0017 closed all three: the row trigger is cloned onto every partition, the `TRUNCATE`
guard is attached to each one, and the application no longer connects as the owner.

**What still holds the guard, today.** The owner role (`VIBEY_PG_MIGRATE_URL`) could still
disable a trigger, so the boundary is that nothing but `vibey migrate` connects as it. A
single-DSN install (the application connecting as the owner or a superuser) still starts,
so an upgrade never strands one, but the worker says so at every start and `vibey doctor`
fails until the roles are split (`infrastructure/db/ledger_guard.py`). The application DSN
is kept out of every engine session and gate command (see
[SECURITY.md](../../SECURITY.md), §5).

**`kind` is open text, read forward-compatibly (vibey#275).** The column has no
constraint and no enum type, so a newer vibey writes a kind an older one has never
heard of. During a rolling upgrade (KEDA-scaled workers on mixed versions) and
after a rollback, older readers meet such rows. Readers must never raise on one:
one row would make the project's whole ledger unreadable to every older worker,
and a lease that dies on it is re-leased to another worker that dies the same way.
So the rule is readers forward compatible, writers strict:

- **Read, kept.** `EventRowMapper` — the one row mapper every reader of this
  table shares — parses `kind` through `domain/ledger.py::EventKindParser`. A
  value this vibey knows is its `EventKind` member. Anything else is an
  `UnrecognizedEventKind` carrying the stored text verbatim; it is never
  dropped and never raised. `LedgerEvent.kind` is `EventKind |
  UnrecognizedEventKind`.
- **Handed on, whole.** The event is in every range, in the full ledger written
  into a receiving worktree (under its own kind, byte for byte what a newer
  vibey writes), and in `digest_range` — which folds `seq` and the payload
  digest, not the kind, so R6 is unchanged. The hash chain folds `kind.value`,
  and an unrecognized kind's value is the stored text, so older and newer
  readers compute the same links.
- **Interpreted by nobody.** Every projection, the no-loss gate's R1–R5 and R7–R8,
  the budget brake and the dashboard match kinds by identity against `EventKind`
  members, so an unrecognized kind matches none of them and is skipped. The
  design ledger's `DesignEvent` view leaves it out explicitly. An older vibey
  therefore cannot act on what a newer kind means. The next engine still gets the
  row in the full ledger.
- **Never written.** `LedgerEventDraft.kind` is `EventKind`, so vibey can only
  append a kind it knows. `to_drafts` refuses to re-append an unrecognized one.

The same exposure existed for `phase` and `provenance` (Postgres enums read into
closed Python enums) and `engine_id` (text read into `EngineId`). vibey#275 covered
`kind`; vibey#287 extended the rule to the other three, so `LedgerEvent.phase`,
`.engine_id` and `.provenance` are `StoredPhase`, `StoredEngineId` and `StoredProvenance`,
and an event with an unrecognised phase or provenance is kept but not `interpretable`
(see [domain-model.md](domain-model.md) §8).

**Search indexes.** `vibey ledger search` (sub-doctrine 7.a, #137) adds three
indexes for the dimensions 0002's could not serve:

```sql
-- 0012_event_search_indexes.sql
CREATE INDEX event_digest              ON event (digest);
CREATE INDEX event_project_produced_at ON event (project_id, produced_at);
CREATE INDEX event_project_engine      ON event (project_id, engine_id, seq);
```

`event_digest` is not unique and must not become so: `digest` is the SHA-256 of
the canonical payload alone, so every event with the same payload (`{}` is common)
shares one. A digest search returns a set; a record is named by `event_id`. The
free-text criterion (`payload::text ILIKE`) has no index — `event_payload_gin` is
`jsonb_path_ops`, which answers containment, not substrings — so it scans one
project's rows.

**The hash chain is derived, not stored.** There is no `prev_hash` column. A
migration's backfill `UPDATE` would be refused by the 0016 triggers (when the chain was
designed, the rules then in force would have discarded it silently), and a column filled
only by new appends would leave all existing history outside the chain.
Instead `domain/ledger_chain.py` recomputes it from the rows: each event's link is
the SHA-256 of the previous link and every column of the event (the payload through
its digest), starting from a per-project genesis. A window of events verifies alone
from the link before it, which is the hook the storage tiers' chunk hashes fold over
(#114).

**The published shard is a projection, not a copy.** `vibey ledger export` (#137)
writes nothing to the database and adds no column: it reads a project's rows, derives
the chain above over **every** event, and writes a JSON Lines file for the repository
to commit — sub-doctrine 7.a's "the shard the repository holds":

```text
{"shard": {"format": "vibey-ledger-shard/v1", "project_id": …, "project_name": …,
           "holds": "full" | "window", "tier": "standard (untiered)",
           "ledger":    {"first_seq", "last_seq", "event_count"},
           "chain":     {"scheme", "head", "findings"},
           "policy":    {"scheme", "fingerprint"},
           "published": {"count", "digest_range"},
           "withheld":  {"events": {<reason>: n, …}, "fields", "paths", "emails", "credentials"},
           "trims":     {<event_id>: {"fields", "paths", "emails", "credentials"}, …}}}
{<one published record: the same object as .vibey/handoff/ledger.jsonl>}
…
```

Each record line is `domain/ledger_record.py`'s object — the one the handoff ledger
writes — after the publication policy (`domain/publication_policy.py`) has run:
default-deny by kind and payload field, engine chatter and `untrusted` events withheld
whole, absolute paths and email addresses replaced, `repo_path` never kept, and
credential redaction (`infrastructure/ledger/redact.py`) last. A record's `digest` is
recomputed over what was published, so every record checks against its own digest,
and `published.digest_range` is `digest_range` over the published records. The
`chain.head` is the ledger's, not the shard's: it commits to the unpublished events
too, so only a holder of the full ledger can recompute it — which is the point, since
it is what an archival node (#114) checks a shard against. The header's counts must
add up (`event_count` = published + withheld) and `vibey ledger site` refuses a shard
whose counts, digests or ranges do not.

**`correlation_id` is the delivery's; `causation_id` is the run's.** Every event
of one delivery — DESIGN, BUILD, REVIEW and the deploy stage set, in every cycle
— carries the same `correlation_id`, so `event_correlation` answers "show me
this whole delivery" in one index scan. The id is *derived* at each write site,
not separately allocated or handed across a process boundary:
`domain/correlation.py` folds the project id into a fixed namespace with `uuid5`,
so every worker computes the same value for the same project. The derived value is
still written on each event -- `event.correlation_id` is `NOT NULL` and
`event_correlation` indexes it -- which is what makes the one-scan query above
possible; what does not exist is an allocator to ask or an id to carry. It is
deliberately not keyed on `cycle` — a
REVIEW loop-back increments the cycle, and one delivery would otherwise acquire
a fresh id each time it went round.

`causation_id` carries what `correlation_id` used to: which engine run produced
this event. `run_and_record` writes the `RunSpec`'s `run_id`, so a row joins to
the run directory on disk, and `build_work_ledger` keys its per-work-thread
projection on it. Events vibey writes on its own account — a finding it raised,
a context packet it compiled — have no causing run and leave it `NULL`.

Both columns already existed. Before this, `correlation_id` was minted with
`uuid4()` at roughly ten separate write sites and `causation_id` was always
`NULL`, so one delivery left behind ten unrelated ids and could be reassembled
only by hand (issue #89).

**Gapless `seq`.** One counter row per project, claimed by an upsert inside the
insert transaction. `PostgresLedgerRepository.append` calls `append_event` inside
`conn.transaction()`:

```sql
-- 0002_event.sql
CREATE TABLE event_seq (
    project_id  uuid PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
    next_seq    bigint NOT NULL DEFAULT 1
);

-- 0009_event_produced_at.sql (the 12-argument overload the repository calls)
CREATE OR REPLACE FUNCTION append_event(
    p_project_id     uuid,
    p_cycle          integer,
    p_phase          phase,
    p_kind           text,
    p_engine_id      text,
    p_job_id         uuid,
    p_causation_id   uuid,
    p_correlation_id uuid,
    p_provenance     provenance,
    p_produced_at    timestamptz,
    p_payload        jsonb,
    p_digest         text
) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE s bigint;
BEGIN
    INSERT INTO event_seq (project_id, next_seq)
    VALUES (p_project_id, 2)
    ON CONFLICT (project_id) DO UPDATE SET next_seq = event_seq.next_seq + 1
    RETURNING next_seq - 1 INTO s;

    INSERT INTO event (
        project_id, seq, cycle, phase, kind, engine_id, job_id,
        causation_id, correlation_id, provenance, produced_at, payload, digest
    ) VALUES (
        p_project_id, s, p_cycle, p_phase, p_kind, p_engine_id, p_job_id,
        p_causation_id, p_correlation_id, p_provenance, p_produced_at, p_payload, p_digest
    );

    RETURN s;
END $$;
```

Migration 0002 created the original 11-argument `append_event` (no
`p_produced_at`), which fell back to the column default and silently replaced the
caller's timestamp with insertion time. Migration 0009 adds the overload above and
keeps the 11-argument function for compatibility. Before the call, the repository
redacts the payload (`infrastructure/ledger/redact.py`) and recomputes `digest`
over the redacted payload, so R6 range digests match what is stored.

Serializing appends per project is intentional. The ledger is the one place where
ordering is the whole point, and a project produces at most a few events per
second — the contention is negligible and the guarantee is absolute. Rule R6 of
the [no-loss gate](handoff-protocol.md#62-the-rules) depends on it.

### 3.3 `job` — the queue

```sql
-- 0003_job.sql
CREATE TYPE job_state AS ENUM (
    'ready','leased','succeeded','failed','awaiting_human','awaiting_capacity','cancelled'
);

CREATE TABLE job (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle             integer NOT NULL,
    phase             phase NOT NULL,
    kind              text NOT NULL,          -- 'build.implement', …
    state             job_state NOT NULL DEFAULT 'ready',
    priority          integer NOT NULL DEFAULT 0,
    work_item_id      text,
    payload           jsonb NOT NULL DEFAULT '{}'::jsonb,
    requirement       jsonb NOT NULL DEFAULT '{}'::jsonb,  -- effort + capabilities + excluded
    idempotency_key   text NOT NULL,
    attempts          integer NOT NULL DEFAULT 0,
    max_attempts      integer NOT NULL DEFAULT 7,
    run_after         timestamptz NOT NULL DEFAULT now(),
    lease_owner       text,
    lease_expires_at  timestamptz,
    assigned_engine   text,
    last_error        jsonb,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    bump_seq          bigint,                 -- 0014: place among bumped jobs; NULL = normal order
    bump_named        boolean NOT NULL DEFAULT false,  -- 0015: in the named set
    CONSTRAINT job_idem_uniq UNIQUE (project_id, idempotency_key),
    CONSTRAINT job_bump_seq_positive CHECK (bump_seq IS NULL OR bump_seq > 0),
    CONSTRAINT job_bump_named_in_lane CHECK (NOT bump_named OR bump_seq IS NOT NULL),
    CONSTRAINT job_lease_consistent CHECK (
        (state = 'leased') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
    )
);

-- The claim index. Partial: only 'ready' rows are ever scanned.
-- (0003 created it on priority/run_after/id; 0014 rebuilt it with bump_seq first.)
CREATE INDEX job_claim
    ON job (project_id, bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC)
    WHERE state = 'ready';

-- The reaper index.
CREATE INDEX job_expiring ON job (lease_expires_at) WHERE state = 'leased';

CREATE TABLE job_dependency (
    job_id            uuid NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    depends_on_job_id uuid NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, depends_on_job_id),
    CONSTRAINT no_self_dep CHECK (job_id <> depends_on_job_id)
);

CREATE INDEX job_dep_reverse ON job_dependency (depends_on_job_id);
```

**`priority`** is set by no request: `EnqueueRequest` has no priority field, so every
enqueued job is 0 and a bump (§3.4, ADR-0054) is the only way to reorder work.

**`idempotency_key`** is `sha256(f"{project_id}:{cycle}:{kind}:{subject}").hexdigest()`
(`domain/job.py::idempotency_key`). Enqueue uses
`ON CONFLICT (project_id, idempotency_key) DO NOTHING` and, on conflict, returns the
existing row, so a handler that crashes after enqueueing but before settling its own
job cannot create duplicate work when the job is replayed.

A handler that enqueues several jobs as one unit uses `enqueue_batch`: the same
per-row statement for every request, all inside one transaction, so a crash part-way
through commits none of them. A request may name its dependencies by idempotency key
(`depends_on_keys`) as well as by job id; a key is resolved inside the transaction,
against the batch's earlier rows first and then `job`, and one that names no job
raises and rolls the batch back rather than enqueueing a job with a dependency missing.
`build.decompose` fans its whole plan out this way (phase-protocols §2.1).

`awaiting_capacity` is defined in the enum, but no repository query sets it today: a
capacity rejection is a `defer` back to `ready` with an explicit `run_after` (§3.4).
`cancelled` is set in two places: the `abandon` answer to a `defect` gate
(`human_gate_repository.py`) and `vibey abandon` (`project_abandonment_store.py`), both
described in §3.9.

### 3.4 Claim, heartbeat, ack, reap

```sql
-- CLAIM
UPDATE job SET
    state            = 'leased',
    lease_owner      = $1,
    lease_expires_at = now() + $2::interval,
    attempts         = attempts + 1,
    updated_at       = now()
WHERE id = (
    SELECT j.id FROM job j
    WHERE j.state = 'ready'
      AND j.run_after <= now()
      AND j.project_id = $3
      AND j.phase::text = ANY($4::text[])   -- only phases this vibey knows (vibey#287)
      AND NOT EXISTS (                      -- never a job of an abandoned project
          SELECT 1 FROM project pr WHERE pr.id = j.project_id AND pr.phase = 'abandoned'
      )
      AND NOT EXISTS (
          SELECT 1 FROM job_dependency d
          JOIN job p ON p.id = d.depends_on_job_id
          WHERE d.job_id = j.id AND p.state <> 'succeeded'
      )
    ORDER BY j.bump_seq ASC NULLS LAST, j.priority DESC, j.run_after ASC, j.id ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING *;

-- HEARTBEAT (every lease/3; default lease 30 s, extended per job kind right after claim)
UPDATE job SET lease_expires_at = now() + $2::interval
WHERE id = $1 AND lease_owner = $3 AND state = 'leased';

-- ACK success
UPDATE job SET state='succeeded', lease_owner=NULL, lease_expires_at=NULL, updated_at=now()
WHERE id = $1 AND lease_owner = $2;

-- NACK with backoff (full jitter, capped at 15 min)
UPDATE job SET
    state            = (CASE WHEN attempts >= max_attempts
                         THEN 'failed' ELSE 'ready' END)::job_state,
    lease_owner      = NULL,
    lease_expires_at = NULL,
    run_after        = now() + (least(power(2, attempts) * interval '2 seconds',
                                      interval '15 minutes') * random()),
    last_error       = $3::jsonb,
    updated_at       = now()
WHERE id = $1 AND lease_owner = $2;

-- GRANT more attempts (ADR-0024; the answered gate's bound reaches the row,
-- because NACK reads 'failed' from the row's own max_attempts). Never narrows.
UPDATE job SET max_attempts = $3, updated_at = now()
WHERE id = $1 AND lease_owner = $2 AND max_attempts < $3;

-- PARK (a human gate was raised; the attempt is refunded)
UPDATE job SET
    state = 'awaiting_human', lease_owner = NULL,
    lease_expires_at = NULL,
    attempts = greatest(attempts - 1, 0),
    updated_at = now()
WHERE id = $1 AND lease_owner = $2;

-- DEFER (capacity rejection: retry at an explicit time; the attempt is refunded)
UPDATE job SET
    state = 'ready', lease_owner = NULL, lease_expires_at = NULL,
    attempts = greatest(attempts - 1, 0), run_after = $3,
    last_error = $4::jsonb, updated_at = now()
WHERE id = $1 AND lease_owner = $2 AND state = 'leased';

-- ASSIGN ENGINE (after rotation selects one)
UPDATE job SET assigned_engine = $3, updated_at = now()
WHERE id = $1 AND lease_owner = $2 AND state = 'leased';

-- GATE ANSWER re-readies the parked job
-- (PostgresHumanGateRepository.answer, same transaction as the answer UPDATE). `run_after`
-- moves up to now, so "claimable since" reads the re-ready, not the first due time.
UPDATE job SET state = 'ready', run_after = greatest(run_after, now()), updated_at = now()
WHERE id = $1 AND state = 'awaiting_human';

-- REAP (each idle worker-loop iteration, before the 5 s LISTEN wait; no separate supervisor)
-- One transaction per lease (PostgresQueueReapStore.reap_leases, ADR-0056): re-read it
-- under its row lock, judge it with domain/queue_reap.py's QueueReapPolicy, move it, and
-- append its QueueReaped event on the same connection. A lease that cannot be moved rolls
-- back alone (LeaseReapIncomplete names it after the rest are reaped).
SELECT id, project_id, cycle, phase, kind, attempts, max_attempts, lease_expires_at
FROM job
WHERE id = $1 AND state = 'leased' AND lease_expires_at < now()
FOR UPDATE SKIP LOCKED;
-- attempts remain: requeue (the claim already counted the attempt)
UPDATE job SET state = 'ready', lease_owner = NULL, lease_expires_at = NULL,
               run_after = greatest(run_after, now()), updated_at = now()
WHERE id = $1;
-- attempts spent: park, refunding one, with a delivery_exhausted human_gate row
UPDATE job SET state = 'awaiting_human', lease_owner = NULL, lease_expires_at = NULL,
               attempts = greatest(attempts - 1, 0), updated_at = now()
WHERE id = $1;
```

All of these live in `PostgresJobRepository`
(`src/vibey/infrastructure/db/job_repository.py`), except the gate-answer
re-ready. PARK and DEFER refund the attempt so that waiting on a human or on
capacity never consumes `max_attempts`; this is how non-negotiable #1 (never
block a worker on a human) and the capacity-rejection rule reach the queue.

NACK's `'failed'` branch is a safety net, not the ordinary end of a job:
`WorkerLoop` checks the bound before it nacks and parks an `attempts_exhausted`
gate instead, GRANTing a wider bound first when the human already answered one
(ADR-0024). A `failed` row therefore means nobody was asked, which is a bug.

The reaper is what makes worker death safe, and is why every handler must be
idempotent (non-negotiable #6): a reaped job *will* be executed again. `vibey
worker`'s drive loop (`cli/main.py`) calls `reap()` only after a `run_once` that
found no claimable job, so a worker busy on long jobs does not reap; another idle
worker, or the next idle iteration, does.

The reap is **bounded** (ADR-0056, closing ADR-0044 §8's gap). A job that kills its
worker on every attempt never reaches `WorkerLoop`'s failure path, so before this it
was re-readied forever; now an expired lease whose `attempts` has reached `max_attempts`
parks with a `delivery_exhausted` gate, refunding one attempt so each answer buys one
more delivery. `SKIP LOCKED` lets two reapers split the expired rows, so a replayed reap
never moves a row twice. A row in a phase this vibey does not know is left for a newer
vibey, as the claim leaves it.

#### Queue priority: bump and un-bump (ADR-0054)

A **bump** puts a job next in line: after whatever is running, ahead of every
un-bumped waiting job, behind every job bumped before it. `bump_seq` is NULL for a
job in normal order; a bump draws it from the sequence `job_bump_seq`
(`src/vibey/infrastructure/db/migrations/0014_job_bump.sql`), so bumped jobs are claimed first-in-first-out by
the order they were bumped, and the order among un-bumped jobs is exactly what it
was. A sequence and not a timestamp: one bump moves a job and its dependencies in
one transaction, where `now()` is one instant for all of them (sub-doctrine 10.g).
`bump_named` (0015, replacing 0014's `bump_origin`) marks the named set: the jobs bumped (or enqueued prioritised) by name and
not since un-bumped. The lane is derived from it -- the named jobs plus all their
unfinished transitive dependencies -- so an un-bump clears the target and every pulled job
the remaining named jobs no longer need, and every bump or un-bump sweeps (and records) any
pulled job a cancelled or failed named job left behind, so no orphan outlives the next admitted
bump or un-bump (a refused request changes nothing).

`PostgresJobPriorityStore` (`src/vibey/infrastructure/db/job_priority_repository.py`)
is reached only through `QueuePriorityService`, which checks the grant first. Each
change is one transaction: `pg_advisory_xact_lock` on the project, a recursive CTE
for the closure the change can reach (a bump's dependencies, stopping at finished
rows), `FOR NO KEY UPDATE` on the rows it may write in id order (never blocking an
enqueue's foreign-key `KEY SHARE`), state read only once locked, the pure planner
in `domain/queue_priority.py`, and the event appended on the same connection:

```sql
-- BUMP (for each job the planner moves, dependencies before what needs them)
UPDATE job SET bump_seq = nextval('job_bump_seq'), bump_named = (id = $target),
               updated_at = now()
WHERE id = $1 RETURNING bump_seq;

-- UN-BUMP (the target, and every pulled job the remaining named jobs no longer need)
UPDATE job SET bump_seq = NULL, bump_named = false, updated_at = now()
WHERE id = ANY($1::uuid[]);
```

A bump never touches `state`, `lease_owner`, `lease_expires_at` or `run_after`,
and the claim's dependency check is unchanged, so a bump orders work and never
admits it. A leased job can be bumped and keeps its place if its attempt returns it
to `ready`. The columns are queue state; the history is the ledger — every request,
moved something, moved nothing or refused, as `JobPriorityBumped`,
`JobPriorityUnbumped` or `JobPriorityRefused` (§3.2).

### 3.5 `work_item`

Provisioned by 0004; not yet read or written by any repository. Work items are
currently carried as `job.work_item_id` and in job payloads.

```sql
-- 0004_work_item.sql
CREATE TYPE work_item_state AS ENUM (
    'pending','implementing','verifying','ready','integrated','blocked','waived'
);

CREATE TABLE work_item (
    item_id         text NOT NULL,            -- 'item-014', stable across cycles
    project_id      uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle           integer NOT NULL,
    title           text NOT NULL,
    state           work_item_state NOT NULL DEFAULT 'pending',
    acceptance_ids  text[] NOT NULL DEFAULT '{}',
    depends_on      text[] NOT NULL DEFAULT '{}',
    branch          text,
    worktree_path   text,
    attempt         integer NOT NULL DEFAULT 0,
    current_effort  smallint NOT NULL DEFAULT 1,   -- Effort IntEnum
    last_engine     text,
    verification    jsonb NOT NULL DEFAULT '{}'::jsonb,
    blocked_reason  text,
    PRIMARY KEY (project_id, cycle, item_id)
);
```

### 3.6 `open_item` — the gate's working set

A projection, rebuildable from `event`. The table exists (0005) but is not yet
populated or read: the [no-loss gate](handoff-protocol.md) rebuilds the open set
in memory from the ledger range on every handoff (`domain/ledger.py::open_items`,
`domain/projections.py`, `domain/noloss.py`). Materializing it is a planned
optimization.

```sql
-- 0005_open_item.sql
CREATE TYPE open_kind AS ENUM ('question','decision','assumption','finding');

CREATE TABLE open_item (
    item_id       text PRIMARY KEY,           -- 'q_7f3a', 'd_44a1', 'a_0c2f', 'f_21c9'
    project_id    uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    kind          open_kind NOT NULL,
    opened_seq    bigint NOT NULL,
    closed_seq    bigint,                     -- NULL = still open
    superseded_by text REFERENCES open_item(item_id),
    blocking      boolean NOT NULL DEFAULT false,
    severity      text,
    ambiguity     text,                       -- 'clear' | 'needs_clarification'
    body          jsonb NOT NULL,
    normalized    text NOT NULL               -- for dedup on restatement
);

CREATE INDEX open_item_open ON open_item (project_id, kind)
    WHERE closed_seq IS NULL AND superseded_by IS NULL;
CREATE INDEX open_item_norm ON open_item (project_id, kind, normalized);
```

`normalized` is meant to hold a lowercased, punctuation-stripped form used to
recognize when an agent restates an existing open question in different words —
which would otherwise create a second id and make the gate demand both. The
normalizer exists (`application/verdict_extraction.py::normalize_text`) but is not
yet wired to this table or to the dispatch path.

### 3.7 `handoff`

```sql
-- 0006_handoff.sql
CREATE TABLE handoff (
    handoff_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle           integer NOT NULL,
    phase           phase NOT NULL,
    job_id          uuid REFERENCES job(id) ON DELETE SET NULL,
    from_engine     text,                     -- NULL when synthesized
    to_engine       text NOT NULL,
    reason          text NOT NULL,
    from_seq        bigint NOT NULL,
    to_seq          bigint NOT NULL,
    range_digest    text NOT NULL,
    envelope        jsonb NOT NULL,
    gate_mode       text NOT NULL,            -- strict | full_transcript | human | forced
    gate_attempts   integer NOT NULL DEFAULT 1,
    gate_violations jsonb NOT NULL DEFAULT '[]'::jsonb,
    accepted        boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT handoff_range_sane CHECK (to_seq >= from_seq)
);

CREATE INDEX handoff_pair ON handoff (project_id, from_engine, to_engine, created_at DESC);
```

`PostgresHandoffRepository.record` writes one row per **accepted** handoff:
`gate_mode` and `gate_attempts` come from the final `GateResult`, and
`gate_violations` holds that result's violations (so `[]` for an accepted gate).
A gate that ends in `HUMAN` parks the job without writing a row, and the
violations of intermediate STRICT attempts are not stored. `job_id` is written as
`NULL`. The only production writer is the wind-down path
(`application/wind_down.py`), so `phase` is always `build` and `reason` is always
`rotation` today. Recording every attempt's violations — so it is measurable which
rules fire most, for which engine pairs, at which phases — is planned.

### 3.8 `engine_health` and `rotation_cursor`

```sql
-- 0007_engine_health_rotation.sql
CREATE TYPE circuit_state AS ENUM ('closed','half_open','open');

CREATE TABLE engine_health (
    project_id       uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    engine_id        text NOT NULL,
    installed        boolean NOT NULL DEFAULT false,
    version          text,
    conformance_ok   boolean NOT NULL DEFAULT false,
    conformance_at   timestamptz,
    auth_ok_at       timestamptz,
    circuit          circuit_state NOT NULL DEFAULT 'closed',
    capacity_state   text,                    -- last classified CapacityState
    resets_at        timestamptz,             -- ONLY ever set for WindowExhausted
    probe_next_at    timestamptz,
    probe_attempt    integer NOT NULL DEFAULT 0,
    consecutive_fail integer NOT NULL DEFAULT 0,
    ewma_failure     double precision NOT NULL DEFAULT 0.0,
    cost_usd_cycle   numeric(12,4) NOT NULL DEFAULT 0,
    selected_count   bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, engine_id),
    CONSTRAINT credits_never_have_a_deadline CHECK (
        capacity_state IS DISTINCT FROM 'CreditsExhausted' OR resets_at IS NULL
    )
);
```

That last `CHECK` is the schema-level expression of the family's hardest-won rule:
**exhausted credits can never carry a reset time.** Conflating it with a rate-limit
window is the exact bug the `*loop` projects exist to avoid, so vibey makes it
impossible to represent, not merely discouraged.

```sql
-- 0007_engine_health_rotation.sql
CREATE TABLE rotation_cursor (
    project_id  uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    engine_id   text NOT NULL,
    current     integer NOT NULL DEFAULT 0,   -- SWRR running value
    "order"     integer NOT NULL,             -- deterministic tie-break
    PRIMARY KEY (project_id, engine_id)
);
```

One row per engine per project. `EngineSelector` (`application/engine_selector.py`)
advances the cursors through `PostgresRotationCursorRepository.update_many`, which
upserts every candidate's row in its own transaction. That happens inside the
handler, after `claim` has already leased the job on a separate connection — the two
writes are **not** in one transaction, despite what the repository docstring says. A
crash between selection and the engine run can therefore advance the cursor without
doing the work; the reaper re-runs the job and the next selection continues from the
advanced cursor. Rotation fairness can skew by one step per crash; no work is lost.
Folding the cursor update into the claim transaction remains open.

### 3.9 `human_gate`

```sql
-- 0008_human_gate_artifact_budget.sql
CREATE TABLE human_gate (
    gate_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    job_id      uuid REFERENCES job(id) ON DELETE CASCADE,
    kind        text NOT NULL,     -- free text; see below
    prompt      text NOT NULL,
    options     jsonb NOT NULL DEFAULT '[]'::jsonb,
    default_answer text,
    answer      jsonb,
    raised_at   timestamptz NOT NULL DEFAULT now(),
    timeout_at  timestamptz,
    answered_at timestamptz,
    answered_by text
);

CREATE INDEX human_gate_open ON human_gate (project_id, raised_at)
    WHERE answered_at IS NULL;

-- 0018_human_gate_answer_once.sql
ALTER TABLE human_gate ADD COLUMN answer_request_id text;
ALTER TABLE human_gate ADD CONSTRAINT human_gate_request_id_with_answer
    CHECK (answer_request_id IS NULL OR answered_at IS NOT NULL);
```

**A gate is answered once.** The answer is a compare-and-set on
`answered_at IS NULL` (`PostgresHumanGateRepository.answer_once`), in one transaction
that also appends a `GateAnswered` event and returns the gate's job to `ready`. Of two
answers racing for one gate exactly one lands. `answer_request_id` names the request
that landed: the same request replayed with the same answer is a no-op, and any other
answer is refused (`GateAlreadyAnswered`) and writes nothing. A gate answered before
0018 has no request id, so every later answer to it is refused.

**An abandonment withdraws a gate on the same compare-and-set.** `vibey abandon` closes
every open gate of the project in the transaction that moves it into abandoned: the row
records `{"withdrawn": true, "reason": "project abandoned"}` as its answer, the abandoning
name as `answered_by`, and `abandon:<project_id>` as its request id, and a `GateWithdrawn`
event records it. No gate row is deleted, and a later answer is refused as a second one.

`kind` is unconstrained text. Values raised by vibey as of 2026-11-24 (a grep of the
`kind=` arguments and `*_GATE_KIND` constants under `src/vibey/`):

| Group | Kinds |
|---|---|
| Conversation | `question`, `choice`, `approval` |
| The queue's own (`QUEUE_GATE_KINDS`) | `attempts_exhausted`, `delivery_exhausted` (the reaper, ADR-0056), `defect` |
| Bounded ladders (ADR-0024) | `escalation_exhausted`, `verify_repair_exhausted`, `integrate_repair_exhausted`, `repair_not_converging` |
| Budget and ULTRA | `budget_exhausted`, `ultra_needs_cap` |
| Engines and handoff | `engine_misconfigured` (exit 78), `handoff_gate_failed`, `handoff_inputs_missing`, `too_many_wind_downs`, `loop_capabilities_unresolved` |
| BUILD and REVIEW | `foreign_branch`, `review_evidence_missing`, `publish_interview` |
| DESIGN | `research_evidence` |
| Deployment | `deploy_interview`, `deploy_acceptance`, `deploy_demo_review`, `deploy_failure_triage` |
| Service bus | `bus_dead_lettered` |

Bounded repair and escalation ladders park on these gates rather than failing (ADR-0024).
Gates are answered with `vibey answer GATE_ID`; `vibey gates` lists the open ones with the
command that answers each. A project may let a few kinds resolve to their stored
`default_answer` after waiting, by declaring `[human_gates] timeout_defaults` (only
`choice`, `deploy_interview`, `deploy_failure_triage`, `deploy_acceptance` and
`deploy_demo_review` may; `domain/gate_timeout.py`). Every other kind waits for a person,
however long, and is reminded about.

An exhausted job whose last `[queue.defect] identical_failures` failures (`JobFailed`
events) share one signature parks on `defect` instead of `attempts_exhausted` or
`escalation_exhausted`: it offers no more attempts, only `requeue` or `abandon`. The
`defect` gate is one of the queue's own (`QUEUE_GATE_KINDS`), and its `abandon` answer
sets the job `cancelled` in the same transaction as the answer, instead of `ready`.

Whether anyone was told a gate is waiting is recorded on the ledger, not on the row: one
`GateNotified` or `GateNoticeUndeliverable` event per gate and notice number, where 0 is
the notice sent when the gate is raised and 1, 2, ... are reminders.

### 3.10 `artifact` and `budget_ledger`

Provisioned by 0008; not yet read or written by any repository. Artifacts are
recorded as `ArtifactProduced` ledger events, and spend as `BudgetSpent` events
summed in memory (`domain/projections.py::build_cost_report`).

```sql
-- 0008_human_gate_artifact_budget.sql
CREATE TABLE artifact (
    artifact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle       integer NOT NULL,
    kind        text NOT NULL,       -- spec | demo | migration | diff | report | transcript
    path        text NOT NULL,
    digest      text NOT NULL,
    produced_by text,
    seq         bigint NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE budget_ledger (
    project_id  uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    cycle       integer NOT NULL,
    phase       phase NOT NULL,
    engine_id   text NOT NULL,
    turns       bigint NOT NULL DEFAULT 0,
    tokens_in   bigint NOT NULL DEFAULT 0,
    tokens_out  bigint NOT NULL DEFAULT 0,
    dollars     numeric(12,4) NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, cycle, phase, engine_id)
);
```

### 3.11 `state_sync` — the state sync's watermark

`vibey state sync` keeps this database and a sealed copy of it on the repository's
`vibey-state` branch the same, both ways
([ADR-0086](../architecture/decisions/0086-state-sync.md)). The merge is three-way, and its
base is the commit this database last agreed with. That commit is kept here, one row per
branch: `remote` is `OWNER/NAME:branch`.

```sql
-- 0022_state_sync.sql
CREATE TABLE state_sync (
    remote       text PRIMARY KEY,
    base_commit  text NOT NULL CHECK (base_commit ~ '^[0-9a-f]{40}([0-9a-f]{24})?$'),
    synced_at    timestamptz NOT NULL DEFAULT now()
);
```

- **Never synced.** It says where *this* database stands, which no other database shares.
  It is in `NOT_SYNCED` (`domain/state_sync.py`) with `schema_migration`, `event_seq` and the
  ACP session tables (3.12), and every other table is in `TABLES`, in the order rows are written.
- **Never granted to the application role.** It is not in `APP_ROLE_GRANTS`
  (`infrastructure/db/ledger_guard.py`), so the worker's DSN can neither read nor move it.
  Only the sync's own DSN (`VIBEY_STATE_PG_URL`) writes it, and that DSN also writes every
  synced table.
- **Moves only after what it marks is durable** (sub-doctrine 10.g). The sync records the
  branch head as the base once the merge is committed here, and the pushed commit once the
  branch has moved to it. A sync that died in between leaves the older base, and the next
  one merges again from it. An upsert that would write the same commit is skipped, so
  `synced_at` is when the base last changed. `base_commit` holds a SHA-1 or SHA-256 commit id.
- **Dropped by `vibey state forget`**, which deletes the branch's row. The next sync then
  merges the two ends as a first sync would, against no base. A row whose commit the branch
  no longer reaches makes the sync refuse until then.

### 3.12 `acp_session` and `acp_session_event` — an ACP session's log

`vibey acp` holds no database credential, so the hub keeps each ACP session and what it
showed, for the principal that created it (SP-ACP; the routes are in
[Hub API: ACP sessions](../reference/hub-api.md#acp-sessions)).

```sql
-- 0023_acp_session.sql
CREATE TABLE acp_session (
    session_id  text PRIMARY KEY,
    cwd         text NOT NULL,
    created_by  text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX acp_session_created_by ON acp_session (created_by, cwd);

CREATE TABLE acp_session_event (
    session_id   text NOT NULL REFERENCES acp_session,
    seq          bigint NOT NULL CHECK (seq >= 1),
    kind         text NOT NULL CHECK (kind IN (
                     'user_message', 'agent_message', 'tool_call', 'tool_call_update',
                     'plan', 'mode', 'attach', 'title', 'closed'
                 )),
    payload      jsonb NOT NULL,
    recorded_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, seq)
);
CREATE INDEX acp_session_event_kind ON acp_session_event (session_id, kind, seq);
```

- **Append-only, by trigger.** `public.ledger_refuse_rewrite()` refuses an UPDATE, a DELETE or
  a TRUNCATE of either table, as it does the ledger's; the application role holds only
  `SELECT` and `INSERT` on them (`APP_ROLE_GRANTS`). A mode change, an attach and a close are
  new rows.
- **Idempotent under replay.** An event is named by `(session_id, seq)`: sending the same event
  again is answered as stored, and a different event at a taken `seq` is refused, never written.
- **Listed by a keyset** over `(updated_at, session_id)`, where `updated_at` is the newest
  event's `recorded_at` (the session's `created_at` before any). The newest event is one probe
  of the primary key and the newest of a kind one probe of `acp_session_event_kind`
  `(session_id, kind, seq)`, so neither a list page nor a load's summary reads a log from its
  start.
- **Bounded per principal** by the hub's `[acp] sessions_max` (sessions, counted over the hub's
  life; `vibey acp` creates one only with its first prompt) and `[acp] session_events_max` (a
  bound on `seq`, so checking it never counts the log). A write past either is refused; nothing
  kept is dropped. There is no retention rule: retiring old sessions is the operator's, with the
  owner role, as for the ledger.
- **Never synced** (`NOT_SYNCED`): a session belongs to the editor on this computer that kept it,
  and two computers appending to one session would diverge at a `seq`, which refuses a merge.

### 3.13 `triaged_ticket` — the GitHub triage queue

The triaged-delivery bridge (`scripts/triage_queue.py`,
[the triaged-delivery runbook](../runbooks/triaged-delivery.md)) orders GitHub issues before
any vibey project exists. GitHub stays the source of an issue's content and labels; this
table is the local, transactional ordering and lease authority (ADR-0054, sub-doctrine 10.g).

```sql
-- 0020_triaged_ticket.sql
CREATE TYPE triaged_ticket_state AS ENUM ('ready', 'leased', 'dispatched', 'blocked', 'completed');

CREATE SEQUENCE triaged_ticket_bump_seq AS bigint;

CREATE TABLE triaged_ticket (
    repository       text NOT NULL,
    issue_number     integer NOT NULL CHECK (issue_number > 0),
    title            text NOT NULL,
    body             text NOT NULL DEFAULT '',
    issue_url        text NOT NULL,
    priority_rank    integer NOT NULL CHECK (priority_rank BETWEEN 0 AND 3),
    bump_seq         bigint,
    state            triaged_ticket_state NOT NULL DEFAULT 'ready',
    project_id       uuid REFERENCES project(id) ON DELETE SET NULL,
    lease_owner      text,
    lease_expires_at timestamptz,
    source_updated_at timestamptz,
    observed_at      timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (repository, issue_number),
    CONSTRAINT triaged_ticket_bump_positive CHECK (bump_seq IS NULL OR bump_seq > 0),
    CONSTRAINT triaged_ticket_lease_consistent CHECK (
        (state = 'leased') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
    )
);

CREATE INDEX triaged_ticket_claim ON triaged_ticket (
    (bump_seq IS NULL), bump_seq ASC NULLS LAST, priority_rank ASC,
    source_updated_at ASC NULLS LAST, issue_number ASC
) WHERE state = 'ready';

CREATE INDEX triaged_ticket_expiring ON triaged_ticket (lease_expires_at)
    WHERE state = 'leased';
```

The claim index orders ready tickets the way `job`'s claim does: bumped tickets first, in
bump order, then by `priority_rank` (lowest first), then the oldest GitHub update.
`project_id` is filled when a ticket is dispatched as a vibey project and becomes `NULL` if
that project row is ever deleted. There is no ORM class for this table.

---

## 4. Notifications

```sql
-- After enqueue (PostgresJobRepository.enqueue, new rows only) and after a gate
-- answer re-readies its parked job (PostgresHumanGateRepository.answer):
NOTIFY vibey_job_ready, '<project_id>';

-- After PostgresHumanGateRepository.raise_gate (emitted; nothing LISTENs yet):
NOTIFY vibey_gate_raised, '<gate_id>';

-- 0019_ledger_appended_notify.sql: after every ledger append, in the inserting
-- transaction, so it is delivered only if the event commits
CREATE TRIGGER event_announce_append
    AFTER INSERT ON public.event
    FOR EACH ROW EXECUTE FUNCTION public.ledger_announce_append();
-- which runs: pg_notify('vibey_ledger_appended',
--                       json_build_object('project_id', NEW.project_id, 'seq', NEW.seq)::text)
```

The hub holds one `LISTEN vibey_ledger_appended` connection (`infrastructure/hub/live.py`)
and wakes each live feed subscribed to that project. A wake-up carries no event: the feed
reads every event after the last `seq` it delivered (sub-doctrine 10.g), so a dropped
notification delays an event and never loses one.

Workers `LISTEN vibey_job_ready` (`infrastructure/db/notifier.py`) and wait at most
5 seconds before polling again, so a missed notification costs latency, never
correctness. No notification is sent on phase changes or when a circuit
half-opens; `EngineHealthService` only schedules `engine_health.probe_next_at`.

---

## 5. Serialization

**Phase transitions** are a compare-and-set on the `project` row, not a lock
(`PostgresProjectRepository.transition`):

```sql
UPDATE project
SET phase = $3, updated_at = now()          -- or: SET phase = $3, cycle = $4, …
WHERE id = $1 AND phase = $2
RETURNING *;
```

Zero rows means the project is no longer in the expected phase — another worker
already moved it, or the job is a replay — and the repository raises `ValueError`.
Handlers that must tolerate replay suppress that miss and continue with idempotent
work (for example `DeployDesignBridgeHandler`). No central process owns transitions;
any number of workers may attempt one and exactly one wins. (`vibey supervisor` exists,
but it only keeps the worker and the delivery bridge running; it never moves a project.)

**A project's caps** (`vibey budget set` / `clear`, `PostgresProjectBudgetStore`) are
changed under a row lock, with their ledger events on the same connection:

```sql
SELECT * FROM project WHERE id = $1 FOR NO KEY UPDATE;
UPDATE project
SET config = (config - $2::text[]) || $3::jsonb, updated_at = now()   -- cleared keys, set keys
WHERE id = $1
RETURNING *;
SELECT append_event(...);                    -- one BudgetCapChanged per changed cap
```

Two changes to one project serialise on the row, so each reads the caps the other
left and records them as its `old`. `NO KEY UPDATE` never blocks the `KEY SHARE` an
event or job insert takes through its foreign key, so a worker keeps writing its
ledger meanwhile. A change that changes nothing runs no `UPDATE` and appends nothing.

**The integration branch** is guarded by a session-level advisory lock scoped to
`(project_id, cycle)` (`PostgresAdvisoryLock`, ADR-0029):

```sql
SELECT pg_try_advisory_lock($1);   -- $1 = signed int64 of sha256('vibey.integrate:<project_id>:<cycle>')[:8]
SELECT pg_advisory_unlock($1);
```

`try_acquire` never blocks; contention is the caller's cue to defer the job. A held
lock pins its pooled connection until release, because returning the connection to
the pool would drop the lock silently.

**Migrations** are serialized by a second session-level advisory lock, under the key
of `sha256('vibey.migrate')`, which a start *waits* for rather than deferring — see §7.

---

## 6. Retention (planned)

Nothing is pruned or garbage-collected today, and every table grows without bound.
`event` is range-partitioned on `seq` since migration 0013, but every row is still in the
one default partition (`event_partitioned_0013_default`): the structure for tiering
exists, and no policy moves rows yet. There is no `vibey gc` command. `vibey ledger`
reads (`show`, `search`) and publishes (`export`, `site`); it never prunes. The intended
policy, none of it implemented:

| Table | Intended policy |
|---|---|
| `event` | **never deleted** — it is the ledger (and the 0016 triggers would refuse a delete). Older ranges move to colder partitions once a project passes ~500k events, keeping the gate's range queries on the hot partition. The original design partitioned by `(project_id, cycle)`; as built, 0013 partitions by `seq` |
| `job` | `succeeded` rows pruned after 30 days; `failed` kept until acknowledged |
| `handoff` | kept with the ledger |
| `artifact` | rows kept; files garbage-collected by a future `vibey gc` when unreferenced by any open item |

---

## 7. Migrations

Plain SQL files in `src/vibey/infrastructure/db/migrations/` — package data, so the
published wheel carries them and a `pip install` finds them where a checkout does
(`MigrationCatalog`, `src/vibey/infrastructure/db/migration_catalog.py`); earlier
references in this document to `migrations/` mean that directory. They are forward-only,
applied in lexical order, tracked in `schema_migration(version, applied_at, checksum)`
(`src/vibey/infrastructure/db/migrator.py`). An install that finds no migration files at
all is refused (`NoMigrationsFound`), never reported as `applied 0`. The migrator creates
that table itself before reading it:

```sql
CREATE TABLE IF NOT EXISTS schema_migration (
    version     text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now(),
    checksum    text NOT NULL
);
```

`version` is the file stem (for example `0011_deployment_stage_set_phases`) and
`checksum` is the sha256 hex of the file's text. Each pending migration runs in its
own transaction together with its `schema_migration` insert.

Migrations run as the schema's owner (ADR-0055), in one of three ways:

- **`vibey migrate`** applies them on `VIBEY_PG_MIGRATE_URL`, then reconciles the
  application role's grants.
- **`build_app()`** in `src/vibey/bootstrap.py` (`SchemaPreparer`), every time it opens
  the pool. It never reads the owner's DSN:
  - on the application's own connection when that role may migrate (a single-DSN
    install);
  - otherwise it only verifies (`PostgresMigrator.pending`, no DDL, no lock) and refuses
    to start while anything is pending.

So every worker start either brings the schema up to date or says why it cannot.
`bootstrap.migrations_dir()` returns `MigrationCatalog.packaged().directory`, the package
data under `vibey/infrastructure/db/migrations/`, the same for a checkout, the container
image and an installed wheel. (It once resolved to a root `<checkout>/migrations` and to
`/app/migrations` in the image; neither exists now.) Every start also re-verifies checksums:
`apply` raises `MigrationChecksumError` if an already-applied migration's file has
changed — an edited migration is a bug, not a convenience. A `check_only=True`
keyword (verify, apply nothing) exists on `apply` but has no CLI flag and no caller
yet. The module-level `apply_migrations(conn, migrations)` is a façade over
`PostgresMigrator().apply` with the default wait; the test harness migrates its
template database through it.

### 7.1 The migration lock

Replicas that start together — a KEDA scale-out, a Helm rollout — would each read the
same applied set and race to apply the same pending migration; on a fresh database
even the `CREATE TABLE IF NOT EXISTS schema_migration` above collides on the
catalog's unique index. So every run takes a session-level advisory lock first, and
holds it until the last pending migration has committed:

```sql
BEGIN;
SELECT set_config('lock_timeout', '300000ms', true);  -- the bound: this statement only
SELECT pg_advisory_lock($1);   -- $1 = signed int64 of sha256('vibey.migrate')[:8]
COMMIT;                        -- the lock is session-level, so it outlives the COMMIT
-- CREATE TABLE IF NOT EXISTS schema_migration; read it; apply each pending
-- migration in its own transaction (as above)
SELECT pg_advisory_unlock($1); -- in a finally: a failed migration wedges nobody
```

One process migrates; the rest queue on the lock, then read a settled applied set and
find nothing to do. The key (`PostgresMigrator.LOCK_KEY`, `-1686359016981790252`) is
derived the way ADR-0029 derives the integrate key, so the two can never collide.
It is a class constant rather than a setting: it is the contract between every
process that migrates one database — the old and new releases of a rolling upgrade
included — and two processes configured with different keys would not exclude each
other at all. Advisory locks are scoped to one database, so separate deployments never
contend and need no key of their own. A test pins the value so it cannot drift
between releases.

**This lock blocks, deliberately.** ADR-0029's never-block clause governs a worker
holding a job, which defers on contention because it has other work it could do. The
migration lock is taken inside `build_app()`, before anything has been claimed, by a
process that cannot do anything until the schema is current; the only alternative to
waiting is exiting and being restarted to wait again.

**The wait is bounded.** `VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS` (default `300`; `0`
waits indefinitely, Postgres's own meaning for `lock_timeout = 0`; fractions round up
to the next millisecond, never down to `0`) sets how long a start queues behind
another process's migration. When it runs out the start fails with
`MigrationLockTimeout`, naming the key and the backend pid still holding it (read
from `pg_locks`, filtered to this database) — so a wedged holder surfaces as a
failed start with a pid to inspect in `pg_stat_activity`, not as a pod that looks
healthy and never arrives. A value that is not a number of seconds between `0` and
Postgres's ceiling (`2147483.647`) fails the start with
`InvalidMigrationLockTimeout` before the pool opens; it is never replaced by the
default. The bound is `SET LOCAL` for the acquiring statement only, so the migrations
themselves never run under it.

`apply` refuses (`MigrationInsideTransaction`) a connection that already has a
transaction open: inside an outer transaction nothing would commit until after the
lock was released, and a second process could read the old applied set anyway.

### 7.2 Tests

`tests/infrastructure/db/test_migrator.py` applies the full set to a fresh Postgres
and asserts the expected tables exist, re-applies the set as a no-op, and re-applies
it over a database that already holds a `project` row. Against real Postgres, with
two sessions on one database, it also proves the lock: two starts racing a slow
migration apply it exactly once (with the lock disabled the same test fails on the
`schema_migration` catalog race); a second start queues on the lock before touching
anything and then finds the schema settled; a bounded wait behind a wedged holder
raises `MigrationLockTimeout` naming the holder's pid, and leaves no `lock_timeout`
or open transaction behind; the lock is released after a run and after a failed
migration; and a migration does not inherit the wait bound. There is no per-version
upgrade fixture yet: no test seeds data at migration N−1 and then applies N.

### 7.3 Every migration, in order

| File | What it does |
|---|---|
| `0001_project.sql` | `project`, the `phase` enum, the original one-project-per-path index |
| `0002_event.sql` | `event` (unpartitioned), `event_seq`, `provenance`, the 11-argument `append_event()`, the first append-only rules |
| `0003_job.sql` | `job`, `job_dependency`, `job_state`, the claim and reaper indexes |
| `0004_work_item.sql` | `work_item` (provisioned, unused) |
| `0005_open_item.sql` | `open_item` (provisioned, unused) |
| `0006_handoff.sql` | `handoff` |
| `0007_engine_health_rotation.sql` | `engine_health` with the credits-never-have-a-deadline `CHECK`, `rotation_cursor` |
| `0008_human_gate_artifact_budget.sql` | `human_gate`, `artifact`, `budget_ledger` |
| `0009_event_produced_at.sql` | the 12-argument `append_event()` that keeps the caller's `produced_at` |
| `0010_visual_design_phase.sql` | adds `visual_design` to `phase` |
| `0011_deployment_stage_set_phases.sql` | adds `deploy_design`, `deploy_execute`, `deploy_review` to `phase` |
| `0012_event_search_indexes.sql` | the three `vibey ledger search` indexes |
| `0013_ledger_partitioning.sql` | rebuilds `event` partitioned by `RANGE (seq)` with primary key `(project_id, seq)` |
| `0014_job_bump.sql` | `job.bump_seq`, `job_bump_seq`, the claim index rebuilt bump-first (ADR-0054) |
| `0015_job_bump_named.sql` | `job.bump_named`, replacing 0014's `bump_origin` |
| `0016_ledger_append_only_guard.sql` | replaces the rules with triggers that refuse `UPDATE`, `DELETE` and `TRUNCATE` (ADR-0055) |
| `0017_ledger_guard_search_path.sql` | pins the guard functions' `search_path` |
| `0018_human_gate_answer_once.sql` | `human_gate.answer_request_id`: a gate is answered once |
| `0019_ledger_appended_notify.sql` | `NOTIFY vibey_ledger_appended` on every append (§4) |
| `0020_triaged_ticket.sql` | `triaged_ticket` (§3.13) |
| `0021_project_repo_live_uniq.sql` | one live project per checkout (§3.1) |
| `0022_state_sync.sql` | `state_sync` (§3.11) |
| `0023_acp_session.sql` | `acp_session`, `acp_session_event` (§3.12) |

---

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `ERROR: the ledger is append-only: UPDATE on event is refused` (SQLSTATE `42501`) | A statement tried to rewrite the ledger; the 0016 trigger refused it | Append a new event that supersedes the old one |
| `permission denied for table event` on `UPDATE`, `DELETE` or `TRUNCATE` | You are connected as the application role, which holds only `SELECT` and `INSERT` | This is correct; corrections are new events |
| `MigrationChecksumError` at start | An already-applied migration file was edited | Restore the file; write a new migration instead |
| `MigrationLockTimeout` naming a pid | Another process has held the migration lock past `VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS` | Inspect that pid in `pg_stat_activity` (§7.1) |
| SQL that joins on `event.event_id` alone is slow or ambiguous | `event_id` is not the key since 0013 | Address events by `(project_id, seq)` |

## Where next

- [handoff-protocol.md](handoff-protocol.md), for how the ledger range is read and verified
  at every handoff.
- [`docs/reference/configuration.md`](../reference/configuration.md#database-roles), for
  the two database roles and their DSNs.
- [ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md),
  for why the guard is triggers and a role, not rules.

## Say it in one line

vibey keeps its queue and its append-only ledger in PostgreSQL: 23 forward-only migrations,
a ledger keyed on `(project_id, seq)` and partitioned by `seq`, and triggers that refuse every
rewrite.
