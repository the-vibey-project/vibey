---
description: vibey appends every decision, question, answer, handoff and cost to a PostgreSQL ledger that its application role cannot rewrite, and each export walks a SHA-256 chain over every event to show an edit.
---

# How do I keep a tamper-evident record of everything an AI agent did?

**Short answer:** vibey appends every decision, question, answer, handoff and cost to a
PostgreSQL ledger that its application role cannot rewrite, and each export walks a SHA-256
chain over every event to show an edit.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For anyone who must later show what an agent did. Split the
> database roles, check `ledger-guard` in `vibey doctor`, and export a chain head to keep
> somewhere else: five commands once PostgreSQL runs. Afterwards a record the application
> cannot rewrite, and a head that shows any edit. Or [see a real one first](../../explorer/index.md).

## The lesson: the bound book

The kettle had just clicked off when Daniel asked the question he had carried all morning.

**Daniel:** Why keep a separate record? The agent's chat transcript says what it did.

**Professor Feynman:** Suppose a shop keeps the day's sales on a slate. Someone wipes one line.
Can you tell?

**Daniel:** No.

**Professor Feynman:** Now write each sale in a bound book, in ink, and beside each line a number
worked out from that line and the number above it. Change one line and every number after it is
wrong. You may add a line; you may never change one. That is vibey's ledger, and the database
itself refuses the eraser.

**Daniel:** Then nobody can cheat.

**Professor Feynman:** Not quite. Someone may write a false new line, and it will be chained like
an honest one. And whoever owns the shop can rebind the book. So you copy the last number to a
notebook you keep elsewhere. The picture stops working in one place: the shop book is one copy,
and ours is checked by the database on every write.

## Steps

**1. Give the application a role that cannot rewrite the ledger.** The owner's string is used
only by `vibey migrate`; the application's role holds `SELECT` and `INSERT` on the ledger and
nothing that could change a row ([database roles](../../reference/configuration.md#database-roles)).

```bash
VIBEY_PG_MIGRATE_URL=postgresql://owner@localhost:5432/vibey vibey migrate
export VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey
```

**2. Check the guard is in force.**

```bash
vibey doctor        # database-security section, near the top: ledger-guard PASS, FAIL or UNKNOWN
```

`ledger-guard` fails if the application role is a superuser, owns the ledger, holds `UPDATE`,
`DELETE` or `TRUNCATE` on it or a partition, or if a guard trigger is missing, disabled or
altered. `UNKNOWN` means `VIBEY_PG_URL` is not set. A worker also warns at every start when the
guard is not in force ([`vibey doctor`](../../reference/cli.md#vibey-doctor)).

**3. Read the record.**

```bash
vibey ledger show --limit 100                       # one line per event, oldest first
vibey ledger search --kind DecisionRecorded --since 2026-09-01 --json
vibey ledger search --actor untrusted               # everything from outside the trust line
```

Each event carries its kind, phase, engine, job, time, a provenance of `trusted`, `agent` or
`untrusted`, and a SHA-256 digest of its payload. A person's change also records the
operating-system account that ran it ([`vibey ledger`](../../reference/cli.md#vibey-ledger)).

**4. Take a chain head, and keep it somewhere else.**

```bash
vibey ledger export PROJECT_ID -o ledger-2026-11-24.jsonl
vibey ledger site --from ledger-2026-11-24.jsonl -o site --json-only   # optional, no database
```

The export walks the chain over every event, withheld ones included, and writes the head into
the shard's header. It prints the head and the sequence number it covers, then `verified`, or
how many disagreements it found and that the head is published unverified. Copy each shard off
the database host. [What gets published](../ledger-publication.md) explains what a shard
withholds.

## What the chain covers

Each event's link is the SHA-256 of the link before it and every stored field: project,
sequence number, id, cycle, phase, kind, engine, job, causation, correlation, provenance, the
time in UTC, and the payload's digest. The first link starts from a hash of the project's id,
so no event can move between projects
([`ledger_chain.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/ledger_chain.py)).

## Daniel's teach-back

**Daniel:** The ledger is a bound book: vibey can add lines but its role cannot change or
delete one, and `vibey doctor` proves that with `ledger-guard`. Each export chains every event
into one head. I keep heads elsewhere, because the owner could still rebind the book.

**Professor Feynman:** Good. And the chain catches a changed line, not a false new one.

## The evidence

| Claim | Where it is proved |
|---|---|
| The database refuses `UPDATE`, `DELETE` and `TRUNCATE`, partitions included | [Migration 0016](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/db/migrations/0016_ledger_append_only_guard.sql); [`test_ledger_guard.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/db/test_ledger_guard.py) |
| The application role cannot switch the guard off | `test_the_application_role_cannot_switch_the_guard_off`, same file |
| The whole test suite runs as the restricted role | [`tests/db_roles.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/db_roles.py) |
| Changing any field of any event breaks the chain | [`test_ledger_chain.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/domain/test_ledger_chain.py) |
| Decisions are written before they take effect | [The ledger invariant](../../paper.md#the-ledger-invariant) |
| The guard is the database's | [ADR-0055](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md) |

## Limits

"Tamper-evident" is smaller than "tamper-proof".

- **The owner can still change the schema**, and a superuser can do anything. Keep the owner's
  string out of every process an agent can reach; vibey hands it to `vibey migrate` alone.
- **The chain shows a rewrite, not a forged append.**
- **Nothing outside your database vouches for the chain.** The head is not signed, timestamped
  by a third party or anchored anywhere, and event times are vibey's own.
- **There is no verify command yet.** The chain is walked on export, which exits 0 even when
  the walk disagrees, so read what it prints. The code that walks it accepts earlier heads.
- **Engine tool calls are recorded after the fact**, translated from the engine's own log.
- **Mapping this to an audit control** is for you and your assessor.

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| `ledger-guard` FAIL | The application role can rewrite, or a trigger is off | Step 1 with two roles, then `vibey migrate` |
| `ledger-guard` UNKNOWN | `VIBEY_PG_URL` is not set | Export it, then rerun |
| The export prints disagreements | The chain does not match the rows | Keep that shard; compare with your earlier heads |

## Where next

- [ADR-0003](../../architecture/decisions/0003-event-sourced-ledger.md): why the ledger is the
  source of truth.
- [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md): the
  database's authentication.

## Say it in one line

vibey writes every agent decision to a ledger its own role cannot rewrite, and each export chains every event into a head you keep elsewhere.

## Improve this guide

If a command printed something other than this page says, or a link does not prove its
claim, that is a good first contribution. This page is
[`docs/guides/outcomes/keep-a-tamper-evident-record.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/keep-a-tamper-evident-record.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. A verify command is a larger contribution this
page would like to link to; [open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
to discuss it first.
