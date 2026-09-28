---
id: skill-10-concurrency-patterns-7ddc3dad7f
purpose: 10 concurrency patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-distributed-concurrency-and-messaging/SKILL.md
requires: ["skill-9-resilience-patterns-ce5e37b7f5"]
links: ["skill-11-integration-and-messaging-a44a5701fe"]
---

## §10. Concurrency Patterns

**[DURABLE] Ordered by preference, and the order is the advice.**

**Don't share** — immutability, thread confinement, actors, per-key sharding. ⚠️ **Almost
always the right answer and the least explored one.**
**Message passing** — actors (Erlang/Akka), CSP channels (Go), queues between stages.
**Structured concurrency** — ⚠️ **the most important recent idea here**: child tasks cannot
outlive their scope, so cancellation and error propagation are well-defined rather than
ad hoc. Now in Kotlin, Swift, Java (virtual threads and scopes), Python's TaskGroups, and
Trio's nursery concept where it originated.
**Producer-consumer with backpressure** — ⚠️ **an unbounded queue is a memory leak that
hides the real problem.** Bound it and propagate the pressure.
**Thread pool / worker pool**, **fork-join**, **pipeline**, **scatter-gather**,
**read-copy-update**, **double-checked locking** (⚠️ **historically a famous source of
subtle bugs**; use your language's lazy-init facility instead).

**⚠️ Async/await is a pattern with a well-known cost**: **function colouring** — async
propagates up your call stack and splits your ecosystem in two. Virtual threads and green
threads are the alternative bet.

---
