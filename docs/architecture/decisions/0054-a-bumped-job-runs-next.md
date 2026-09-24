# 0054 — A bumped job runs next: after what is running, ahead of all un-bumped work, first in first out, and only the operator or a declared source may bump

**Status:** accepted (cited by #1089, the storm's priority lane, and by #1091, vibey's job queue; the storm conforms to items 4–7 once #1092 merges — see *Conformance* below) · **Date:** 2026-09-24 · **Cites:** sub-doctrines 8.c, 12.j, 12.h and 10.f, and 10.g, 12.d, 12.f, SD-01 §2/§4 · **Related:** ADR-0002, ADR-0003, ADR-0016, ADR-0044, ADR-0051, ADR-0053 · **Evidence:** `develop` at `255f3f4a`: the claim at `src/vibey/infrastructure/db/job_repository.py:198` ordered `priority DESC, run_after ASC, id ASC`, `priority` existed on `EnqueueRequest` and `JobRecord`, and no caller, command or flag ever set it to anything but `0`

**Owes:** nothing new as conduct — this record is mechanism (ADR-0020). It applies
ratified conduct: 8.c (one run at a time; waiting is ordered, visible and safe), 12.j
(an unattended run admits no stranger), 12.h (the grant is declared in reviewed TOML) and
10.f (every request's outcome is on the record, and the queue shown is the queue as it
is). It owes the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
`README.md` and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in
`properdocs.yml`, and the claim's ordering wherever it is written down:
`docs/plans/data-model.md` §3.3–§3.4, `docs/plans/architecture-and-roadmap.md` and the
paper's queue semantics.

## Context

The operator's request: *"The system should be able to push a priority item into the queue
and have that run next so that it doesn't have to wait for the other jobs in front of it."*
Then: *"both queues need priority features."* Asked who may push an item to the front, the
operator chose: *"Operator and declared sources — your account plus automation you declare
in config; a GitHub label or issue from anyone else can never jump the queue (12.j)."*

There are two queues, and the operator asked for one design. vibey's is the PostgreSQL
`job` table, claimed with `FOR UPDATE SKIP LOCKED` (ADR-0002, ADR-0044). The storm's is the
lane queue under `docs/plans/qwenstorm-3.0.0`, over `queue.txt` and an append-only priority
log (#1089). This record states the contract both keep, numbered as the storm's
`tools/storm_queue.py` docstring numbers it, and then vibey's mechanism.

vibey's queue had half a priority feature and none of the other half: the claim ordered by
`priority DESC`, the column existed, and nothing could set it. A priority number, had there
been a way to set it, would not have said what the operator asked for either. "Run next" is
a position, not a weight.

## Decision: the contract (both queues)

1. **Next means next after whatever is running.** A bump never preempts a claimed, leased
   or running item and never touches its lease (8.c: one instance, one run at a time; every
   job idempotent under replay). It changes only what starts after it.
2. **Priority items run first, first in first out,** in the order they were bumped, ahead
   of every un-bumped waiting item. Among un-bumped items the order is exactly what it
   was. Bumping an item that is already a priority item keeps its place.
3. **Dependencies are respected and pulled forward.** Bumping an item whose dependencies
   are unfinished bumps those dependencies too, transitively, dependencies before what
   needs them, keeping their relative order, and the result names every item moved. A bump
   never makes an item runnable before its dependencies finish. **A dependency that can
   never finish — failed, cancelled or abandoned, unknown, or part of a cycle — refuses the
   bump, naming it.**
4. **Authorisation.** Only two callers may bump or un-bump:
   - the **operator**: the account that owns the queue's reviewed declaration, verified by
     the operating system — the process's uid against the owner of that file (or of the
     state directory it lives in) — never by a name typed on a command line or read from an
     environment variable;
   - an **automation that names itself** with `--source NAME`, where the reviewed
     declaration lists `NAME` under `[queue.priority] sources` (vibey) or `[priority]
     sources` (storm), **and** the request runs as the operator's account. A declared name
     is not a credential.

   The declaration is read only from the queue's own reviewed configuration — never from
   the working directory or a path the caller chooses. Its absence is refusal (12.f).
   Nothing reads the forge to decide priority: no label, issue or comment from anyone can
   reach it (12.j). And priority never bypasses any other gate — phases, human gates,
   admission, a capacity deferral, the budget brake, the handoff no-loss gate: those decide
   whether an item may run; a bump decides only which runnable item runs first.
5. **Recorded, append-only, visible.** **Every** bump and un-bump request is recorded,
   whatever became of it — moved something, moved nothing, or refused — with who asked and
   why. Authorisation comes **before** any lookup of the item, so a stranger asking about any
   item, real or not, is refused and recorded without learning anything about it. The
   record is append-only; the queue can be shown in the order it will run, with every
   priority item marked.
6. **Reversible, by derivation.** "The priority lane is exactly: the set of items bumped
   (or enqueued prioritised) BY NAME and not since un-bumped, plus all their unfinished
   transitive dependencies, ordered FIFO by when each item first entered the lane.
   Un-bumping X removes X from the named set; it is refused (naming them) while another
   named item depends on X. Everything else follows by derivation, so no orphan can
   remain." The un-bump's record lists exactly the items it `removed` from the lane.
7. **A new item can be enqueued already prioritised, in one step,** through the same grant.
   Bumping or re-enqueueing an item that has already finished is a recorded no-op: nothing
   moves, the record says why, and the request succeeds, as a plain re-enqueue of a
   finished item does.

## Decision: vibey's mechanism

**Ordering: a column, a sequence, and a flag for the named set.** `job.bump_seq bigint` is
NULL for a job outside the lane; a job entering it takes `nextval('job_bump_seq')`, and
keeps it for as long as it stays. `job.bump_named boolean` is true for a job in the named
set -- bumped or enqueued prioritised by name, not since un-bumped -- and false for one
pulled in as a dependency. The claim becomes

```sql
WHERE ... AND j.phase::text = ANY($known_phases)
ORDER BY j.bump_seq ASC NULLS LAST, j.priority DESC, j.run_after ASC, j.id ASC
FOR UPDATE SKIP LOCKED LIMIT 1
```

and the partial claim index is rebuilt on the same key (`migrations/0014_job_bump.sql`).
Every bumped job sorts before every un-bumped one; bumped jobs sort by the order their
numbers were drawn. The `priority` column keeps its place in the order, but no request can
set it any more: `EnqueueRequest.priority` is removed, because a priority on the request
was a second way to reorder work with no grant. A bump is the only way; `priority` is 0 for
every enqueued job. A sequence and not a
timestamp: one bump moves a job and its dependencies in one transaction, where `now()` is
the same instant for all of them (10.g). Not a large `priority`: first-in-first-out would
need a counter disguised as a weight, and an un-bump would have to remember what it
overwrote.

**The lane is derived (item 6).** `bump_named` replaced 0014's `bump_origin` in
`migrations/0015_job_bump_named.sql`, which also clears any pulled job the per-bump rule had
left in the lane with nothing named needing it. An un-bump takes the target out of the named set and, in
the same transaction, clears `bump_seq` on every pulled job the remaining named jobs no
longer need -- wherever it came from -- so the lane afterwards is exactly its derivation.
A job pulled in and later bumped by name keeps its number and joins the named set. A
property test (a Hypothesis state machine) drives random, overlapping bumps and un-bumps,
including the sequence that exposed the orphan in the per-bump rule (x, d, a needing d, b
needing d: bump a, bump b, un-bump a, un-bump b), and asserts after every step that the
lane equals the derivation, and that un-bumping every named job clears it.

**The claim stays strict.** The claim selects only jobs in a phase this vibey knows, and
every `PostgresJobRepository` read maps `phase` and `state` strictly, as it always did: a
worker is never handed a job it cannot vouch for (vibey#287). Only `vibey queue list` and
the priority store read forward-compatibly, so one row a newer vibey wrote cannot make the
queue unreadable — and the store refuses to write such a row.

**It holds under concurrency.** Every reorder takes a transaction-scoped advisory lock on
its project, so reorders of one project never interleave. It then locks the rows it can
write `FOR NO KEY UPDATE`, in id order — `NO KEY`, so an enqueue naming one of them as a
dependency (which takes `KEY SHARE` for its foreign key) is never blocked — and reads their
state only once the locks are held. A bump's closure stops at finished rows: it reads a
finished dependency (to know it succeeded, or that it never will) but never walks or locks
past it. The claim takes its row `FOR UPDATE SKIP LOCKED`, so it passes over a row a reorder
holds; a reorder that meets a row a claim holds waits for the claim to commit, then sees the
job running and moves it without touching the lease. Should the database still break a lock
cycle by aborting a reorder, it becomes `ReorderConflict` — a recorded refusal naming the
job and saying a retry is safe — never a traceback. Five workers claiming at once take
exactly the first five in order (`tests/infrastructure/db/test_job_priority_repository.py`,
against real PostgreSQL).

**The pure rule lives in the domain.** `domain/queue_priority.py` holds the ordering key,
the grant, the bump planner (closure, dependencies first, relative order kept, a dependency
that can never finish or a ring refused) and the un-bump planner. It has no I/O and no
clock: the store hands it a locked snapshot and the caller and time come in from outside.

**The scaler counts what the claim takes.** KEDA's scaler query carries the same
known-phase filter as the claim, pinned to `Phase` by its test, so a job no worker of this
release will claim never scales one up. `vibey queue list` shows such a job without a
place in line, marked as not claimable by this vibey.

**Authorisation.** The reviewed declaration is `vibey.toml` at the root of the repository
the project record names — the path `bootstrap` resolves for the project — and nowhere
else:

```toml
[queue.priority]
sources = ["storm"]   # automations the operator admits, exactly as they name themselves
```

The operator is the account that owns that file, or the repository root when there is no
file; the process's uid is compared with the owner's, and the account's name comes from the
password database, never `$USER`. A repository nobody owns admits nobody. A missing file
declares no source; a malformed one refuses every request, recorded, because "I could not
read the declaration" and "there is no declaration" are different facts (10.f); the same
holds for a declaration or a repository the process is not permitted to read, or that is
not text. `operator` is reserved and never declarable.

**What the grant separates, and what it does not.** The grant separates *operating-system
accounts*: a request from any account but the one owning the reviewed declaration is
refused. It does not separate *processes* running under the operator's uid. vibey's own
engines run as the worker's uid, which is the operator's in a local install, and until
`fix/engine-env-no-db-credentials` lands they also inherit the database DSN — so an engine
could reach the queue directly, below the grant, as any other process of that account
could. That PR is the fix for the credential half. This record does not claim the grant
bounds an engine, and nothing here should be read as saying it does.

**One way in.** `bootstrap.build_app` builds `QueuePriorityService` and exposes only the
service on `AppResources`; the Postgres store is built there and handed to nothing else, so
no entry point — the CLI, the Kubernetes operator, a handler written next year — can
reorder the queue past the grant (a test pins it). The service finds the project, reads the
grant, decides, and only then asks the store; whatever the store refuses (an unknown job,
a finished one, a job in an unknown phase, a dependency that can never finish, a ring,
bumped dependents, a lock conflict) is recorded as `JobPriorityRefused` before it reaches the
caller.

**Recorded.** `JobPriorityBumped`, `JobPriorityUnbumped` and `JobPriorityRefused`, each
filed under the project's current cycle and phase, with `by` (`operator:NAME`,
`source:NAME` or `account:NAME`), the job named, what moved, what was already ahead, and a
note when nothing moved. A change's event is appended in the same transaction as its row
writes. A refused request is `untrusted` provenance: it came from outside the grant, so its
text is data (SD-01 §4).

**The surface.** `vibey queue list [PROJECT]`, `vibey queue bump JOB [--project P]
[--source NAME]` and `vibey queue unbump JOB [...]`, each with `--json`; `vibey design
resume PROJECT --priority` for item 7. There is no `--config`: the grant is never a path
the caller supplies.

### Conformance: the storm lane at `8281351e`

The contract above is the one both queues are held to. The storm lane as merged in #1089
(`8281351e`) does not yet keep items 4–7 in these respects:

- **Item 4.** A declared `--source` is admitted from any uid, not only the operator's; and
  the account name comes from `getpass` (`$USER`, `$LOGNAME`), not the password database.
- **Item 5.** A request refused as `Invalid` — an unknown slug, an item that is not
  prioritised, a settled item — raises without being recorded; only authorisation
  refusals reach the priority log.
- **Item 6.** An un-bump removes only the item: it leaves the dependencies its bump pulled
  forward prioritised, and it does not refuse while a prioritised item depends on it.
- **Item 7.** Pushing an item that has already settled raises without a record, rather
  than being a recorded no-op.

These close when the storm hardening PR (`fix/storm-priority-hardening`, #1092) merges.
Until then this record claims conformance for vibey's queue only.

### Where the two queues differ below the contract

- **The declaration and its anchor.** vibey reads `<repo>/vibey.toml` `[queue.priority]
  sources`, anchored on that file's owner; the storm reads `storm.toml` `[priority]
  sources`, anchored on the owner of `queue.txt`.
- **The record.** vibey records on the project ledger, in the same transaction as the row
  change; the storm appends one JSON line per request to its priority log and derives the
  lane order by replaying it.
- **A refused request's exit code.** vibey exits 3 (a guarded command blocked by a domain
  rule, as every vibey refusal does); the storm exits 1.
- **What cannot be recorded.** vibey records every request against the project it names. A
  request naming no project that exists, or a project in a phase this vibey does not know,
  has nowhere it can be recorded; it is reported and goes no further.

## Consequences

A bump is the operator's lever over what runs next and nothing more. It cannot rush a job
past a gate, past a deferral a capacity rejection set, or past a dependency, and it cannot
take a run away from the worker holding it.

**Rolling deploys.** The migration rebuilds the claim index inside its own transaction, so
claims — and every other write to `job` — stall until it commits, for as long as building
the index over the table's ready rows takes. A worker still running the previous release
then claims by the old order and ignores `bump_seq` until it is replaced: during a rolling
upgrade a bump is honoured by the new workers only. Old workers neither read nor write the
new columns, so the migration is safe under them, but "runs next" holds once every worker
runs this release.

Anything that rewrites the claim statement must keep `bump_seq ASC NULLS LAST` at the head
of its order and the known-phase filter. The repository tests pin the claim's order against
the domain's key, and pin that a job in an unknown phase is never claimed. If ADR-0044's
bus dispatch replaces the Postgres claim as the default, the dispatcher must publish in this
order, and the contract above is what it is measured against.

Two concurrent bumps of different projects may commit in the opposite order from the one
in which they drew their numbers; within a project the advisory lock serialises them.

## Alternatives considered

**Set `priority` very high.** Rejected above: no first-in-first-out among bumped work
without a counter, and an un-bump that has to remember what it overwrote.

**A timestamp column (`bumped_at`).** Ties within one transaction, and clock readings across
hosts are not a sequence. 10.g.

**Preempt the running job.** Contrary to 8.c and to idempotent replay. "Next" is next.

**Let anyone with a label bump.** A label is text anyone with triage rights can set; the
operator ruled it out by name, and 12.j forbids it.

**Read the grant from the working directory, or a `--config` path.** A grant the caller can
point at is a grant the caller writes. Rejected in review.

**Trust a declared source name on its own.** A name is not a credential; any process could
type it. The source must also run as the operator's account.

**Report a dependency that can never finish, and bump anyway.** The bumped job would hold a
place it can never use. Refused instead, naming the dependency — as the storm does.

**Cascade an un-bump to the dependents.** It sends back work the operator bumped by name
without being asked. Refused instead, naming the dependents, so the operator decides.

**Record only requests that moved something.** A refused or empty request is exactly the
one worth reading afterwards (12.d). Every request is recorded.
