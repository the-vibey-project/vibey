---
id: skill-15-anti-patterns-table-34e43a81d7
purpose: 15 anti patterns table
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: ["skill-14-anti-patterns-d930c26b28"]
links: ["skill-16-contested-questions-c66c5dfb07"]
---

## §15. Anti-Patterns Table

| Anti-pattern | Why |
|---|---|
| Learning patterns as a catalogue to install | **"Conformity to patterns is not a measure of goodness"** — Ralph Johnson, GoF co-author (§1 → `patterns-foundations-gof-and-alternatives`) |
| Adding a pattern that makes the code harder to explain | That's the signal it's premature (§2.3 → `patterns-foundations-gof-and-alternatives`) |
| Hand-rolling Iterator in a language with iteration | ⚠️ The language is the pattern (§3.1 → `patterns-foundations-gof-and-alternatives`) |
| Singleton for shared state | **Global mutable state with a nice name** (§14) |
| Interface with exactly one implementation "for testing" | Modern test tooling fakes concrete types (§5 → `patterns-foundations-gof-and-alternatives`) |
| Service Locator instead of DI | Hides dependencies rather than declaring them (§5 → `patterns-foundations-gof-and-alternatives`) |
| Container magic you can't trace by reading | Runtime failures where compile-time ones belonged (§5 → `patterns-foundations-gof-and-alternatives`) |
| Hexagonal architecture over a CRUD app | ⚠️ **If domain logic is thin, you don't need it** (§6.2 → `patterns-architectural`) |
| Tactical DDD without the strategic work | Ceremony without the benefit (§6.3 → `patterns-architectural`) |
| Microservices when teams aren't blocked on deploys | Paying the cost, not collecting the benefit (§7 → `patterns-architectural`) |
| Microservices that must deploy together | ⚠️ **Distributed monolith** (§14) |
| Adopting a hyperscaler's architecture at 1/10000th the scale | Cargo cult (§14) |
| Writing to your DB then publishing an event | ⚠️ **The dual-write problem. Real systems lose orders this way** (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Event Sourcing for CRUD | ⚠️ **Four months for a two-week feature, then rewritten** (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Choreographed saga past ~3 steps | Becomes impossible to reason about (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Treating compensation as rollback | The intermediate state was visible (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Synchronous external call with no circuit breaker | Cascading failure (§9 → `patterns-distributed-concurrency-and-messaging`) |
| Retry without jitter | Thundering herd (§9 → `patterns-distributed-concurrency-and-messaging`) |
| Retrying non-idempotent operations | Duplicates (§9 → `patterns-distributed-concurrency-and-messaging`) |
| **Any network call without a timeout** | ⚠️ **The most under-set config in software** (§9 → `patterns-distributed-concurrency-and-messaging`) |
| Unbounded producer-consumer queue | A memory leak hiding the real problem (§10 → `patterns-distributed-concurrency-and-messaging`) |
| Double-checked locking by hand | Famously subtle; use the language's lazy init (§10 → `patterns-distributed-concurrency-and-messaging`) |
| Promising exactly-once delivery | At-least-once + idempotency is the achievable target (§11 → `patterns-distributed-concurrency-and-messaging`) |
| Event-carried state transfer by default | Couples consumers to your internal schema (§11 → `patterns-distributed-concurrency-and-messaging`) |
| Agent where a workflow would do | ⚠️ **Prefer predefined code paths** (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| Multi-agent for a single-agent task | Over-applied buzzword (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| Agentic loop with no iteration cap | A financial failure mode (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| Prompts embedded in orchestration code | Treat prompts as versioned artifacts (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| Framework chosen before pattern | Backwards (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| Big-bang rewrite | Use Strangler Fig (§13 → `patterns-llm-agentic-and-legacy-migration`) |
| Schema change without expand-contract | The only safe way under live traffic (§13 → `patterns-llm-agentic-and-legacy-migration`) |
| "We might need this later" | ⚠️ **The most expensive sentence in software** (§14) |

---
