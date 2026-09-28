---
id: skill-8-distributed-data-patterns-1e9acbef75
purpose: 8 distributed data patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-distributed-concurrency-and-messaging/SKILL.md
requires: []
links: ["skill-9-resilience-patterns-ce5e37b7f5"]
---

## §8. Distributed Data Patterns

**[DURABLE in force, VERSIONED in tooling.] These exist because the moment you split your
data across services you lose ACID transactions, and everything here is a way of buying
back some consistency guarantee.**

| Pattern | What it solves | ⚠️ Costs |
|---|---|---|
| **Transactional Outbox** | **The dual-write problem** — write to your DB *and* publish an event atomically, by writing the event to an outbox table in the same transaction and relaying it after | A relay process; at-least-once delivery |
| **Inbox / Idempotent Consumer** | Deduplicating received messages | Storage of processed IDs |
| **Idempotency keys** | Preventing duplicate processing of client requests | Key management and retention |
| **Saga** | A business operation spanning services, as a sequence of local transactions with **compensating transactions** for rollback | ⚠️ **Compensation is not rollback** — the intermediate states were visible |
| **CQRS** | Separate write and read models, so each can be shaped and scaled independently | ⚠️ Two models, and eventual consistency between them |
| **Event Sourcing** | State as an append-only log of events; current state is a fold | ⚠️ **The highest-cost pattern here.** Schema evolution of events, replay complexity, and a genuinely different mental model |
| **CDC / log tailing** | Publishing changes by reading the DB transaction log (Debezium) | Coupling to the DB's log format |

> **⚠️ GOTCHA — the dual-write problem is the one to internalize**, because it's how
> real systems lose data quietly. A documented case: a team migrating to microservices
> **immediately started losing orders — the order service committed a row to its own
> database, then called an inventory service to reserve stock, and the two operations were
> not atomic.** Any failure between them leaves the system inconsistent with no error
> raised. **The outbox pattern exists for exactly this, and skipping it is the most common
> serious mistake in event-driven systems.**

**Saga: choreography vs. orchestration.** Choreography — services react to each other's
events, no coordinator. Orchestration — an explicit coordinator drives the steps. **A
reasonable published heuristic: choreography up to 2–3 steps; orchestration at 4+ or when
the logic is complex**, because choreographed flows past that point become impossible to
reason about. **[VERSIONED] Dedicated workflow engines (Temporal, and similar) are
increasingly the answer for orchestration** rather than hand-rolling it.

> **⚠️ GOTCHA — Event Sourcing is dramatically over-applied, and the cautionary tales are
> consistent.** One documented case: **a user-profile service — GET/PUT on name, email,
> address, a team of three juniors — chose full Event Sourcing. Result: four months for a
> CRUD that should have taken two weeks, state-reconstitution bugs that were impossible to
> debug, and a rewrite as conventional REST in three weeks.** The published rule of thumb
> worth carrying: **start with the simplest pattern that meets the need — plain event
> notification covers most cases, CQRS most of the remainder, and Event Sourcing is for
> the small fraction where a full audit trail is a non-negotiable business requirement.**

**[DURABLE] Compose deliberately.** Event Sourcing + CQRS + Outbox is a genuinely common
production combination — **but layer them on only when the system needs them**, starting
from pub/sub as the primitive.

---
