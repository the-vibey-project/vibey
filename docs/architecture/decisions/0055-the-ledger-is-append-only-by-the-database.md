# 0055 — The ledger is append-only by the database, not by convention: triggers refuse every rewrite, and the application connects as a role that could not rewrite it anyway

**Status:** accepted · **Date:** 2026-09-24 · **Cites:** the CLAUDE.md non-negotiable "The ledger is append-only", sub-doctrines 12.j, 12.c, 12.h, 12.e and 10.f, SD-01 §4 · **Related:** ADR-0002, ADR-0016, ADR-0017, ADR-0018, ADR-0025, ADR-0029 · **Evidence:** `develop` at `f7b2dfeb`, checked on 2026-09-24 against a scratch database with all migrations applied (PostgreSQL 18), connected as the table owner, and against the Helm chart at the same commit

**Owes:** nothing new as conduct. This record is mechanism (ADR-0020): it makes an existing
non-negotiable true in the database, and it applies ratified conduct. That conduct is 12.j
(text a model reads can steer an unattended run, so what that run can reach is bounded by
machinery, not by the model's judgement), 12.c and 12.h (roles, grants and DSNs are
declared and reconciled from the repository), 12.e (the upgrade step an operator must take
is checked by the machine) and 10.f (the check reports what it could not determine as
unknown, never as a pass). It owes:

- the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
  `docs/index.md` (`tests/meta/test_adr_counts.py`);
- a nav entry in `properdocs.yml`;
- `SECURITY.md` §7, `docs/reference/configuration.md#database-roles`,
  `docs/reference/cli.md` (`vibey migrate`, `vibey doctor`) and `docs/plans/data-model.md`.

## Context

CLAUDE.md: *"The ledger is append-only. No updates, no deletes. Corrections are new events
that supersede prior ones."* Migrations 0002 and 0013 enforced it with two rules on the
partitioned parent: `CREATE RULE event_no_update/event_no_delete ... DO INSTEAD NOTHING`.
Checked against the migrated schema, as the role vibey connected as:

| Attempt | Result |
|---|---|
| `UPDATE event ...` | 0 rows. The rule fires, but silently. |
| `UPDATE event_partitioned_0013_default ...` | **The row changed.** A rule on a partitioned parent does not fire for a statement addressed to a partition. |
| `DELETE FROM event_partitioned_0013_default ...` | **The row was deleted.** |
| `TRUNCATE event` | **The ledger was emptied.** Rules never fire on `TRUNCATE`. |
| `ALTER TABLE event DISABLE RULE event_no_update; UPDATE event ...` | **Rows changed.** The owner can switch a rule off. |

That role was the owner, and in the Helm chart a superuser as well: the worker's
`VIBEY_PG_URL` named `postgres.user`, the image's `POSTGRES_USER`. So "append-only" held
against vibey's own queries and against nothing else. The DSN had also reached every engine
session (#1093). An unattended session that model-read text could steer held the means to
rewrite or erase the ledger, and nothing would record it.

A second finding came from the operator's machine. `env -i PATH=… HOME=… USER=… psql -w -h
/tmp -d postgres` connected as the superuser with no password. The local server trusts its
socket, the common default for a developer's PostgreSQL. On such a server, any process
running as the operator's OS user connects as a superuser whatever DSN it was given, and
no grant can stop it.

## Decision

1. **Triggers replace the rules** (migration 0016).
   - A `BEFORE UPDATE OR DELETE` row trigger and a `BEFORE TRUNCATE` statement trigger on
     `event` call `ledger_refuse_rewrite()`. It raises `the ledger is append-only: <op> on
     <table> is refused` (SQLSTATE `42501`), with a hint naming this record.
   - The row trigger is on the partitioned parent, so PostgreSQL clones it onto every
     partition that exists and every partition attached later.
   - PostgreSQL does not clone the statement-level `TRUNCATE` trigger.
     `ledger_guard_partitions()` attaches it to every partition that lacks it, at any
     depth. It runs in the migration and again on every migration run.
   - The rules are dropped. A rewrite is refused out loud instead of becoming a silent
     no-op, and a cascading `DELETE FROM project` is refused rather than erroring
     obscurely.
   - The triggers bind the owner too. An owner can still disable a trigger, so the
     triggers are not the boundary; item 2 is.
2. **Two roles, two DSNs, declared and reconciled.**
   - **The owner** (`VIBEY_PG_MIGRATE_URL`) runs migrations and owns every table. Nothing
     else uses it.
   - **The application role** (`VIBEY_PG_URL`) is what every worker, CLI command,
     operator and KEDA scaler connects as. It owns nothing.
   - The application role holds exactly `APP_ROLE_GRANTS` (`infrastructure/db/ledger_guard.py`).
     These were derived from the application's own queries: on `event`, `SELECT` and
     `INSERT` only; on every other table only what some query needs; no `DELETE` or
     `TRUNCATE` anywhere; `USAGE` on `job_bump_seq`; `EXECUTE` on `append_event`.
   - `DatabaseRoleReconciler` runs as the owner on every migration run. It revokes
     everything the application role holds and grants exactly the declared set, so a grant
     added by hand does not survive the next start.
   - It creates the application role when the role is missing and its DSN carries a
     password. It refuses a role that is a superuser, the owner, or a member of the owner.
   - `vibey migrate` does all of this, then connects as the application role and inspects
     the guard. It exits 1 when the guard is not in force.
3. **Where each DSN goes.**
   - In the Helm chart, the owner's DSN is mounted only into a `migrate` init container
     (worker and operator). The workloads get the application's DSN.
   - `build_app()` migrates only on an owner connection when `VIBEY_PG_MIGRATE_URL` is set.
   - Without the owner's DSN, `build_app()` migrates on the application's connection only
     when that role may migrate: a superuser or a member of the migration catalog's owner.
     That is a single-DSN install.
   - Otherwise it verifies the schema without DDL and refuses to start on a stale one
     (`SchemaNotMigrated`).
   - The test harness runs the whole suite this way. `VIBEY_PG_URL` names a restricted
     role and repositories are handed its pool, so an undeclared privilege fails as
     `permission denied`.
4. **The upgrade is detected, not remembered (12.e).** Existing installs run as one
   superuser DSN. They keep working: nothing strands them. But:
   - `vibey doctor` and `vibey doctor --cluster` fail the `ledger-guard` check whenever the
     application's role is a superuser, owns the ledger, holds `UPDATE`, `DELETE` or
     `TRUNCATE` on it or a partition, or finds a trigger missing or disabled;
   - `vibey worker` says so on stderr at every start;
   - `vibey migrate` exits 1.

   The path: set `VIBEY_PG_MIGRATE_URL` to the current (owner) DSN, give `VIBEY_PG_URL` a
   new role name and password, and run `vibey migrate`, which creates that role and grants
   it.
5. **Password-less access is checked too.** The split protects the ledger only once the
   owner and every superuser need a password to connect. `LocalAuthProbe` finds out two
   ways:
   - it attempts an empty-password connection as each of them, on the application DSN's
     host and, when that host is local, on each local socket directory;
   - it reads `pg_hba_file_rules` where the role may.

   A connection let in, or a `trust`/`peer`/`ident` rule that can match them, fails the
   `local-auth` check. A pass needs every attempt refused and the rules read clean.
   Anything less is `UNKNOWN`: printed as such, never a pass, and not a failure. vibey does
   not change `pg_hba.conf`; that is the operator's decision (SECURITY.md §7 gives the
   lines).

## Consequences

**Good.** A holder of the application's DSN cannot `UPDATE`, `DELETE` or `TRUNCATE` the
ledger or a partition, and cannot disable a trigger: that is privilege, checked by
PostgreSQL. The owner is refused by the triggers, loudly. A single-role install is reported
at every start and fails `vibey doctor` until it is split. A server that lets a
password-less connection in as a privileged role fails `vibey doctor` too.

**Costs.** Every migration run reconciles grants, a handful of statements. A new query that
needs a privilege fails its tests until `APP_ROLE_GRANTS` declares it. The chart grows an
init container and a second Secret key. On PostgreSQL 14, `public` still grants `CREATE` to
every role, so the application role can create tables there. That cannot touch the ledger,
and `may_migrate` does not mistake it for the owner.

**Not closed.**
- The owner can still disable the triggers. The owner's DSN is the thing to guard: it
  reaches only the `migrate` step.
- A superuser can do anything; hence item 5.
- The `job` and `project` tables are mutable by design. Their integrity rests on the
  queue's own semantics and the ledger, not on this record.

## Alternatives rejected

- **Keep the rules and add more rules.** Rules still never fire on `TRUNCATE` or on a
  partition, and they fail silently.
- **Triggers alone.** The worker was the owner and could disable them.
- **A `SECURITY DEFINER` append function as the only write path, with `INSERT` revoked.**
  It is stronger in principle, but `append_event` is already the only insert path in code.
  It would need the function owned by a third role and a search-path discipline this
  schema does not have yet. It is a reasonable next step; it is not needed for append-only.
- **Refuse to start while the guard is not in force.** Every existing install would stop at
  upgrade. A loud report plus a failing `vibey doctor` makes the step impossible to miss
  without stranding anyone.
