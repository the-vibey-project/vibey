---
description: vibey appends every decision, question, answer, handoff and cost to a PostgreSQL ledger that its application role cannot rewrite, and each export walks a SHA-256 chain over every event to show an edit.
---

# How do I keep a tamper-evident record of everything an AI agent did?

**Short answer:** vibey appends every decision, question, answer, handoff and cost to a
PostgreSQL ledger that its application role cannot rewrite, and each export walks a SHA-256
chain over every event to show an edit.

**See it rather than read about it:** the [ledger explorer](../../explorer/index.md) opens a
real project's public ledger, checks each record's digest in your browser, and shows the hash
chain head that covers every event, withheld ones included.

When an agent's work is questioned later — by a reviewer, a customer or an auditor — a chat
transcript is weak evidence: it lives in one vendor's session, and anyone with access can
change it. vibey keeps its own record instead. Each fact is a row in an append-only table
in your own database, written as the work happens, and the database itself refuses to
change a row once it is there
([ADR-0055](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)).

## Steps

**1. Give the application a role that cannot rewrite the ledger.** Two connection strings:
the owner's, used only by `vibey migrate`, and the application's, used by everything else.
The application role holds `SELECT` and `INSERT` on the ledger and nothing that could
change a row ([database roles](../../reference/configuration.md#database-roles)).

```bash
VIBEY_PG_MIGRATE_URL=postgresql://owner@localhost:5432/vibey vibey migrate
export VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey
```

**2. Check the guard is in force.**

```bash
vibey doctor        # ends with ledger-guard: PASS, FAIL or UNKNOWN
```

`ledger-guard` fails if the application role is a superuser, owns the ledger, holds
`UPDATE`, `DELETE` or `TRUNCATE` on it or a partition, or if a guard trigger is missing,
disabled or altered ([`vibey doctor`](../../reference/cli.md#vibey-doctor)). A worker also
warns at every start when the guard is not in force.

**3. Read the record.**

```bash
vibey ledger show --limit 100                       # one line per event, oldest first
vibey ledger search --kind DecisionRecorded --since 2026-09-01 --json
vibey ledger search --actor untrusted               # everything from outside the trust line
```

Each event carries its kind, phase, engine, job, time, a provenance of `trusted`, `agent`
or `untrusted`, and a SHA-256 digest of its payload. A change a person makes, such as a
budget cap, also records the operating-system account that ran the command
([`vibey ledger`](../../reference/cli.md#vibey-ledger)).

**4. Take a chain head, and keep it somewhere else.**

```bash
vibey ledger export PROJECT_ID -o ledger-2026-09-30.jsonl
```

The export walks the hash chain over every event, withheld ones included, and writes the
chain head into the shard's header. It prints the head and the sequence number it covers,
then `verified`, or how many disagreements the walk found and that the head is published
unverified. Copy each shard off the
database host, so the record of what the head was cannot be rewritten by whoever can
rewrite the database. [What gets published](../ledger-publication.md) explains what the
shard withholds, and why.

## What the chain covers

Each event's link is the SHA-256 of the link before it and every stored field of the event:
project, sequence number, id, cycle, phase, kind, engine, job, causation, correlation,
provenance, the time in UTC, and the payload's digest. The first link starts from a hash of
the project's id, so no event can move between projects. Changing any field of any event
changes its link and every link after it; changing a payload without its digest shows as a
digest the payload no longer produces ([`ledger_chain.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/ledger_chain.py)).

## The evidence

| Claim | Where it is proved |
|---|---|
| The database refuses `UPDATE`, `DELETE` and `TRUNCATE`, partitions included | [Migration 0016](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/db/migrations/0016_ledger_append_only_guard.sql); [`test_ledger_guard.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/db/test_ledger_guard.py) |
| The application role cannot switch the guard off | `test_the_application_role_cannot_switch_the_guard_off` in the same file |
| The whole test suite runs as the restricted role | [`tests/db_roles.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/db_roles.py) |
| Changing any field of any event breaks the chain | [`test_ledger_chain.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/domain/test_ledger_chain.py) |
| Decisions are written before they take effect | [The ledger invariant](../../paper.md#the-ledger-invariant), in the research paper |

## Limits

"Tamper-evident" is a precise promise, and it is smaller than "tamper-proof".

- **The owner can still change the schema.** The database's owner can disable a trigger or
  detach a partition; a superuser can do anything. ADR-0055 lists what it does not close.
  Keep the owner's connection string out of every process an agent can reach; vibey
  hands it to `vibey migrate` alone.
- **The chain shows a rewrite, not a forged append.** A role that may insert can insert a
  false event; the chain then links it like any other.
- **Nothing outside your database vouches for the chain.** The head is not signed,
  timestamped by a third party, or anchored anywhere; event times are supplied by vibey
  itself. That is why step 4 copies each head elsewhere.
- **There is no verify command yet.** The chain is walked when you export. No command
  compares an earlier head with the ledger as it stands, though the code that walks the
  chain accepts such anchors. The export also exits 0 when its walk disagrees, so read what
  it prints.
- **Engine tool calls are recorded after the fact.** Decisions, answers and gate outcomes
  are written as they happen; an engine's turns and tool calls are translated from its own
  log once it has written them.
- **Mapping this to an audit control is your call.** vibey supplies the record and the
  checks above. Whether they satisfy a given framework's control is for you and your
  assessor to decide.

## Go deeper

- [The ledger invariant](../../paper.md#the-ledger-invariant), with the formal statement.
- [ADR-0003](../../architecture/decisions/0003-event-sourced-ledger.md) on why the ledger is
  the source of truth, and ADR-0055 on how the database enforces it.
- [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md), for the
  database's authentication.

## Improve this guide

If a command printed something other than this page says, or a link does not prove its
claim, that is a good first contribution. This page is
[`docs/guides/outcomes/keep-a-tamper-evident-record.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/keep-a-tamper-evident-record.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. A verify command is a larger contribution this
page would like to link to; [open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
to discuss it first.
