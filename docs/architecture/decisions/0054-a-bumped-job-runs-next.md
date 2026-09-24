# 0054 — A bumped job runs next: after what is running, ahead of all un-bumped work, first in first out, and only the operator or a declared source may bump

**Status:** proposed · **Date:** 2026-09-24 · **Cites:** sub-doctrines 8.c, 12.j, 12.h and 10.f, and 10.g, 12.d, 12.f · **Related:** ADR-0002, ADR-0003, ADR-0016, ADR-0044, ADR-0051, ADR-0053 · **Evidence:** `develop` at `255f3f4a`: the claim at `src/vibey/infrastructure/db/job_repository.py:198` ordered `priority DESC, run_after ASC, id ASC`, `priority` existed on `EnqueueRequest` and `JobRecord`, and no caller, command or flag ever set it to anything but `0`

**Owes:** nothing new as conduct — this record is mechanism (ADR-0020). It applies
ratified conduct: 8.c (one run at a time, and waiting is ordered, visible and safe), 12.j
(an unattended run admits no stranger), 12.h (the grant is declared in TOML) and 10.f
(the queue shown is the queue as it is). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md` (`tests/meta/test_adr_counts.py`),
a nav entry in `properdocs.yml`, and the claim's ordering wherever it is written down:
`docs/plans/data-model.md` §3.3–§3.4, `docs/plans/architecture-and-roadmap.md` and the
paper's queue semantics.

## Context

The operator's request: *"The system should be able to push a priority item into the queue
and have that run next so that it doesn't have to wait for the other jobs in front of it."*
Then: *"both queues need priority features."* Asked who may push an item to the front, the
operator chose: *"Operator and declared sources — your account plus automation you declare
in config; a GitHub label or issue from anyone else can never jump the queue (12.j)."*

There are two queues. vibey's is the PostgreSQL `job` table, claimed with
`FOR UPDATE SKIP LOCKED` (ADR-0002, ADR-0044). The storm's is the lane queue under
`docs/plans/qwenstorm-3.0.0`, built in its own pull request (#1089). This record is the
contract both implement; the storm's lane cites it. The mechanism section below is vibey's.

vibey's queue already had half a priority feature and none of the other half. The claim
ordered by `priority DESC`, the column existed, and the DTOs carried it — but nothing could
set it: no flag, no command, no way to move a job that was already waiting. And a priority
number, had there been a way to set it, would not have said what the operator asked for.
"Run next" is a position, not a weight.

## Decision

### The contract (both queues)

1. **"Next" means next after whatever is running.** A bump never preempts a claimed or
   leased job. 8.c runs one instance per loop and, on the operator's own hardware, one run
   at a time; the run in flight finishes, and every job stays idempotent under replay. A
   bump never touches a lease.
2. **Bumped jobs run first, in the order they were bumped,** ahead of all un-bumped waiting
   work. Among un-bumped work the order is exactly what it was.
3. **Dependencies are respected and pulled forward.** Bumping a job whose dependencies are
   unfinished bumps those dependencies too, transitively, dependencies before what needs
   them, keeping their relative order; the result lists everything moved. A bump never
   makes a job claimable before its dependencies succeed.
4. **Authorisation.** Only the operator, or a source declared in configuration, may bump or
   un-bump. The command line run by the operator is the operator. Anything else is refused,
   and the refusal is recorded and reported (12.j, 12.d). The absence of a declaration is
   refusal, not permission (12.f): with nothing declared, the operator alone may reorder.
   A work item that came from an outside author never becomes eligible for a bump by an
   undeclared source, because no undeclared source can bump anything.
5. **No safety bypass.** Priority changes order and nothing else. Phases, human gates,
   admission, a capacity deferral's `run_after`, the budget brake and the handoff no-loss
   gate all apply exactly as before: they decide whether a job may run; a bump decides only
   which claimable job runs first.
6. **Recorded, append-only, visible.** Every bump and every un-bump appends one event to
   the ledger, in the same transaction as the rows it changes, naming the source and every
   job moved. The ledger is append-only; the row's ordering field is queue state and the
   ledger is its history. The queue can be shown in claim order with every bump marked.
7. **Reversible.** An un-bump returns a job to normal order and is recorded the same way.

The storm's queue implements this contract over `queue.txt` and an append-only priority log
(`docs/plans/qwenstorm-3.0.0/tools/storm_queue.py`, `[priority] sources` in `storm.toml`).
Where the two differ below the contract, the difference is named in the mechanism that has
it.

### vibey's mechanism

**Ordering: one nullable column and a sequence.** `job.bump_seq bigint` is NULL for a job in
normal order; a bump sets it from `nextval('job_bump_seq')`. The claim becomes

```sql
ORDER BY j.bump_seq ASC NULLS LAST, j.priority DESC, j.run_after ASC, j.id ASC
FOR UPDATE SKIP LOCKED LIMIT 1
```

and the partial claim index is rebuilt on the same key (`migrations/0014_job_bump.sql`).
Every bumped job sorts before every un-bumped one (NULLS LAST); bumped jobs sort by the order
their numbers were drawn, which is the order they were bumped; un-bumped jobs keep the old
order untouched. The existing `priority` column keeps its meaning as a band among un-bumped
work.

Why a sequence and not a timestamp: one bump moves a job and its dependencies in one
transaction, where `now()` is the same instant for all of them, and first-in-first-out
among them needs a strict order a clock cannot give. 10.g says it plainly — a timestamp is
not a position. Why not a large `priority`: first-in-first-out would need each new bump to
outrank the last, which is a counter pretending to be a weight, and an un-bump would have to
remember the number it replaced. A NULL is its own normal order; clearing it is the whole
un-bump.

**It holds under concurrency.** The claim takes the first row in this order that no other
transaction holds; with several workers claiming at once, the set they take is the front of
the queue in order, and no two take the same row
(`tests/infrastructure/db/test_job_priority_repository.py`, against real PostgreSQL). A bump
locks its closure `FOR UPDATE`, in id order so overlapping bumps wait rather than deadlock,
and reads each row's state only once its lock is held. A bump that meets a row a claim is
taking waits for the claim to commit, then sees the job running and moves it without
touching the lease; a claim that meets a row a bump holds passes over it, as `SKIP LOCKED`
always has. Dependencies are written once, at enqueue, so the closure found before the
locks is the closure that holds after.

**What cannot be moved is reported.** A dependency that cannot run and cannot be moved —
failed, cancelled, or in a state this version does not know — is listed as blocking the
target, not skipped over; the target still cannot run until someone resolves it.

**An un-bump sends back what cannot run without it.** Because a bumped job cannot run before
its dependencies, un-bumping a dependency also un-bumps every bumped job that depends on it
— the mirror of the pull-forward — so a bump never holds a place its job cannot use. The
storm's queue reports those dependents instead and leaves them prioritised; neither lets a
job past a dependency, so both keep the contract.

**A running job can be bumped, and a running dependency is pulled.** Its lease is untouched;
the number only matters if the attempt returns the job to the queue, where it then keeps its
place instead of falling to the back.

**The pure rule lives in the domain.** `domain/queue_priority.py` holds the ordering key, the
bump planner (closure, dependencies first, relative order kept, a ring refused rather than
broken arbitrarily), the un-bump planner and the grant. It has no I/O and no clock: the
store hands it a locked snapshot and the time comes from the caller.

**Authorisation: the operator, and `[queue.priority] sources`.** Every command the operator
runs speaks as the source `operator`, which is admitted without a declaration and cannot be
declared. Any other source must be named in `vibey.toml`:

```toml
[queue.priority]
sources = ["storm"]   # the automations that may bump, exactly as they name themselves
```

`vibey queue bump JOB --source storm` is how a declared automation identifies itself. An
undeclared name is refused: the store appends `JobPriorityRefused` with `untrusted`
provenance — the request came from outside the grant, so its text is data (SD-01 §4) — and
the command exits 3 with the reason and where to look. A missing file declares nothing; a
malformed one is an error, never an empty grant, because "I could not read the declaration"
and "there is no declaration" are different facts (10.f). A source that relays other
people's words — a label anyone may set, an issue comment — is a stranger however it is
named, and declaring one widens the grant to everyone who can reach it; that is the
operator's decision to make in a reviewed diff, and the reason the list exists.

A source is a name, not a credential, and this record does not pretend otherwise: whoever
can run `vibey` against the database already holds the operator's account. What the grant
governs is which of the operator's own automations may reorder the queue, and it makes any
code path that would carry a stranger's request — a label handler, an issue-comment
trigger — fail closed and leave a record, instead of relying on nobody ever writing one.

**Recorded.** `JobPriorityBumped`, `JobPriorityUnbumped` and `JobPriorityRefused` are new
event kinds. A change's event is appended on the same connection, in the same transaction,
as the row writes: both commit or neither does. A replayed request that moves nothing
appends nothing — it is not a second bump, and the ledger does not say it was.

**The surface.** `vibey queue list [PROJECT]` shows running work, then waiting work in claim
order, each bumped job marked with its number and each job's unfinished dependencies
counted. `vibey queue bump JOB` and `vibey queue unbump JOB` take `--source`, `--config` and
`--json`. `vibey design resume PROJECT --priority` enqueues the interview already bumped
through the same grant; the application service's `enqueue` does the same for any caller
that builds its own request.

## Consequences

A bump is the operator's lever over what runs next and nothing more. It cannot rush a job
past a gate, past a deferral a capacity rejection set, or past a dependency, and it cannot
take a run away from the worker holding it.

Anything that rewrites the claim statement must keep `bump_seq ASC NULLS LAST` at the head
of its order. The repository tests pin the claim's order against the domain's key on a
mixed queue, and fail when either drifts. If ADR-0044's bus dispatch replaces the Postgres
claim as the default, the dispatcher must publish in this order, and the contract above is
what it is measured against.

Two concurrent bumps may commit in the opposite order from the one in which they drew
their numbers. The order is the drawing order — the moment each bump was made — which is
the only order either request can see.

A dependency ring cannot be bumped. The planner refuses rather than choosing which job of
the ring runs first; nothing in the ring could ever be claimed anyway, and the refusal names
the ring.

## Alternatives considered

**Set `priority` very high.** Rejected above: no first-in-first-out among bumped work
without a counter, and an un-bump that has to remember what it overwrote.

**A timestamp column (`bumped_at`).** Ties within one transaction, and clock readings across
hosts are not a sequence. 10.g.

**Preempt the running job.** Contrary to 8.c and to idempotent replay: the run in flight
finishes. "Next" is next.

**Let anyone with a label bump.** A label is text anyone with triage rights can set; the
operator ruled it out by name, and 12.j forbids it — a stranger does not direct the run.

**Record the bump only in the row.** A row can be updated; the ledger cannot. The history of
who moved what, and who was refused, belongs where corrections are new events.
