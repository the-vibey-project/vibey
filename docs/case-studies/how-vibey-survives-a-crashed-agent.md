---
description: When an AI coding agent crashes mid-task, vibey loses no job and commits no job twice — leases, an append-only ledger and parked human gates, with the chaos test that proves it and the costs it pays.
---

# How vibey survives a crashed agent

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** When an agent dies mid-task, vibey loses no job and commits
> no job twice. Work is leased from a PostgreSQL queue, every fact is in an append-only ledger,
> and a question for a person is a parked job, not a waiting thread. After a crash, start a
> worker again; `vibey recover` releases a dead worker's jobs at once. A chaos test proves it on
> every full CI run. vibey is 0.4.0 and under active development.

## The lesson: the library loan

The library was closing, and the librarian was walking the shelves with a trolley of returns.

**Daniel:** Professor, if an AI agent crashes halfway through a task, isn't the task just lost?

**Professor Feynman:** Think of a library. You do not own the book you borrow; you have it for two
weeks. Renew it and you keep it. Disappear, and when the two weeks are up it goes back on the
shelf for the next reader.

**Daniel:** So a crashed worker is a reader who disappeared.

**Professor Feynman:** Exactly. vibey lends each job to one worker at a time, for a fixed time, and
a live worker keeps renewing. A dead one stops, the loan runs out, and the job goes back on the
shelf.

**Daniel:** What if the reader turns up late and tries to hand in the book after someone else has
borrowed it?

**Professor Feynman:** That is the gap, and the librarian closes it: a return from anyone but the
current borrower is refused. In vibey, a worker whose lease was handed on can no longer commit
the job. The picture stops working at the notes in the margin: a library book carries none, but
vibey's job does. What the agent learned is in the ledger, not in the agent, so the next worker
reads it there.

## The problem: a session is a single point of failure

An AI coding agent is a program, and programs die. A laptop lid closes. The operating system
kills a process that ran out of memory. Kubernetes stops a pod to scale in. A vendor's credits
run out halfway through a task. When the agent was the only place the work lived, the work dies
with it.

A single agent session keeps three things in memory, and each fails in its own way when the
session dies:

- **The claim.** Either nobody remembers the task was started, so it is lost, or two workers
  both think it is theirs, so it is done twice.
- **The knowledge.** The decisions, assumptions and open questions sit in a transcript shaped
  by one vendor, which the next engine cannot read.
- **The waiting.** A session that stopped to ask a person a question holds its task hostage
  until the person answers, or until the session dies.

This page tells how vibey is built so that none of those events loses a job: the fixes that do
not work, the design that does, the evidence, and what the design costs. Every claim links to
the decision record, test or paper section behind it.

## Three fixes that look right and are not

**"Mark the row as taken."** The usual job queue on a single-file database flags a row as
locked and then works on it. If the worker dies after setting the flag, the row stays locked
forever. SQLite, the obvious local choice, has no row-level locking to do better. Surviving
worker death is the requirement, so a queue that leaks on crash was ruled out
([ADR-0002](../architecture/decisions/0002-postgres-not-sqlite.md)).

**"Ask the old agent to summarise for the new one."** A summary written by a model drops
constraints, open questions and deferred findings, and it drops them *silently*: nothing in
that code path can report what was lost
([ADR-0004](../architecture/decisions/0004-no-loss-gate-on-handoff.md)).

**"Wait until the credits come back."** An engine that has spent its credits is not rate
limited. No amount of waiting fixes it. vibey keeps the two apart at three layers: the
`CreditsExhausted` type has no reset time and never may, a property test checks it, and a
database constraint refuses one.

## The design: three rules

### 1. Work is borrowed, never owned

Workers claim jobs from a PostgreSQL queue with `SELECT … FOR UPDATE SKIP LOCKED`, which gives
each job to exactly one worker without any global lock. A claim is a **lease**: it expires
unless the worker renews it, and a live worker renews it every third of its length. The lease
is sized to the job
([`bootstrap.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/bootstrap.py)):

| Job | Lease |
|---|---|
| Building and verifying a work item (`build.implement`, `build.verify`) | 2 hours |
| Planning, decomposing and integrating (`build.plan`, `build.decompose`, `build.integrate`) | 15 minutes |
| Publishing a finished project (`review.publish`) | 15 minutes |
| Everything else | 2 minutes |

When a worker dies, it simply stops renewing. A reaper returns every expired lease to the ready
state while the job has attempts left, and parks it for a person once they are spent, so a job
that crashes every worker it touches is bounded rather than retried forever
([ADR-0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md)).
Every write that settles a job is **fenced on the lease owner**: a worker whose lease was
reaped and handed on can no longer commit the job, so a late finisher cannot overwrite the one
who now holds it.

The paper states the consequence precisely: *a crashed worker costs at most one lease of delay
and never a lost item* ([Queue semantics](../paper.md#queue-semantics)).

### 2. The conversation lives in a ledger, not in a session

Every decision, question, answer, assumption and finding is an event in an append-only ledger
in PostgreSQL, written *before* it takes effect. The state of a delivery at any moment is a
function of the ledger up to that moment, nothing else
([ADR-0003](../architecture/decisions/0003-event-sourced-ledger.md)). No vendor holds the only
copy, so any engine can pick up where any other stopped.

"Append-only" is enforced by the database, not by good intentions: triggers refuse every update
and delete, and the application connects as a role that could not rewrite the ledger anyway
([ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)). A
SHA-256 hash chain over every event makes any edit visible
([`ledger_chain.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/ledger_chain.py)).

When an engine winds down mid-task, for example because it ran out of credit, vibey writes the
cycle's full ledger into the receiving worktree, writes a handoff brief for the next engine, and
checks the brief with a **no-loss gate**: a pure, deterministic predicate, with no model call,
that rejects the brief if any open question, decision, assumption or finding is missing. It
matches on ids that vibey mints, not on wording. A failing brief is regenerated with the
violations fed back, up to three times; then the whole transcript is handed over; then a person
is asked. It never proceeds on a failed gate
([ADR-0004](../architecture/decisions/0004-no-loss-gate-on-handoff.md)).

### 3. A person is never a thread waiting on a keyboard

When a job needs a human answer, the worker writes the question as a gate row *before* it
releases the job, marks the job as awaiting a person, and moves on to other work. Nothing sits
blocked on input. Your answer, given with `vibey answer`, makes the job ready again in the same
transaction ([ADR-0009](../architecture/decisions/0009-human-gates-are-parked-jobs.md)).

Two smaller choices finish the picture. Each work item is built in its own git worktree, so one
crashed item's half-edited files never touch another's
([ADR-0008](../architecture/decisions/0008-worktree-isolation.md)). And in a container, `tini`
runs as the first process and forwards the stop signal, so a worker being shut down drains its
current job instead of dying mid-write
([ADR-0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md)).

## Daniel's teach-back

**Daniel:** A worker borrows a job for a set time and keeps renewing; if it dies, the loan runs
out and another worker takes the job, and the old one can no longer commit it. What the agent
knew is in the ledger, so the next engine reads it there, after a check that nothing was
dropped. And a question for me is a parked job, so no worker waits on me.

**Professor Feynman:** That is it. One correction: the job may *run* twice, if a slow worker's
loan runs out. It is only *committed* once.

## The evidence

**The chaos test.**
[`tests/infrastructure/db/test_chaos.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/db/test_chaos.py)
runs 8 workers against a real PostgreSQL queue of 500 jobs, with a 150-millisecond lease and a
reaper running beside them. On each claim a worker abandons the job with probability 0.2: no
acknowledgement, no heartbeat, exactly what a killed process leaves behind. The test passes
only if every job reaches a final state, none is lost, and none is committed twice. It counts
honestly: it prints how many times the work ran, how many of those runs committed, and how many
late commits the lease fence refused, and the three must balance. The file is a protected test,
changed only with the maintainer's sign-off.

**The no-loss property suite.** CI runs the handoff gate's properties at 10,000 generated
examples each, as a job of its own whose check is required on `develop` and `main`
([`ci.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/ci.yml)).
A pull request's own run skips it when the diff touches no Python, and a skipped required check
passes; the merge queue's run and the nightly run are full, so it runs there.

**Every supported database.** The database suite runs on PostgreSQL 14 to 18 in CI's full tier:
every merge-queue run, every pull request into `main`, and every night. A pull request's own run
uses the oldest and newest, 14 and 18
([`ci-matrices.toml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/ci-matrices.toml)).

## What it costs

A design is honest only if it names its price.

- **Work can run twice; it commits once.** Delivery is at-least-once. A worker slower than its
  lease (a loaded machine is enough) has its job reaped and claimed by another, so the work may
  run twice even though only one run commits. That is why every job must be idempotent under
  replay.
- **Recovery waits for the lease.** A build whose worker vanished is picked up when its two-hour
  lease runs out, not at once. An operator who knows the worker is gone can release its jobs
  immediately with [`vibey recover`](../reference/cli.md#vibey-recover).
- **It needs a database server.** PostgreSQL 14 or later, not a file on disk. That is the price
  of row-level locking.
- **One fallback still trusts the reader.** When the gate hands over the whole transcript, the
  next engine receives it as a file named in its prompt rather than inlined, so that path relies
  on the engine reading the file. The decision record names this as open work.
- **The test simulates the kill.** The chaos test abandons jobs inside one process rather than
  killing separate operating-system processes; its own docstring says so and says why.

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| A job stays leased after its worker died | The lease has not run out yet | Wait it out, or `vibey recover --project PROJECT_ID --stop-workers --dry-run` to see what would be stopped and reset, then run it without `--dry-run` |
| A `handoff_gate_failed` gate | A handoff brief could not pass the no-loss gate | Fix what it names, then answer it; an answer alone re-queues a job that parks again |
| `vibey gates` shows a gate you forgot | The job parked and is waiting for you, not lost | Answer it with the command `vibey gates` prints |

## What this means when you run it

Close the lid, kill the worker, or let an engine run dry: start a worker again and the queue
carries on from where the ledger says it stands. `vibey gates` lists every question still
waiting for you, and `vibey recover` releases a dead worker's jobs without waiting out the
lease.

## Read further

- [Queue semantics](../paper.md#queue-semantics) and [The no-loss handoff gate](../paper.md#the-no-loss-handoff-gate)
  in the research paper, with the formal statements.
- [ADR-0002](../architecture/decisions/0002-postgres-not-sqlite.md),
  [ADR-0003](../architecture/decisions/0003-event-sourced-ledger.md),
  [ADR-0004](../architecture/decisions/0004-no-loss-gate-on-handoff.md),
  [ADR-0009](../architecture/decisions/0009-human-gates-are-parked-jobs.md),
  [ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md) and
  [ADR-0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md):
  the decisions, each with the alternatives it rejected.
- [Contributing](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour):
  run the chaos test yourself in your first hour.

## Say it in one line

vibey lends each job to one worker on a renewable lease and keeps every fact in an append-only ledger, so a crashed agent costs a delay, never a lost or doubled job.
