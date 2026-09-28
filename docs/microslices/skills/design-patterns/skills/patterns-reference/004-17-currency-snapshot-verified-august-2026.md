---
id: skill-17-currency-snapshot-verified-august-2026-2f9cef220e
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: ["skill-16-contested-questions-c66c5dfb07"]
links: ["skill-18-the-canon-301417ec6b"]
---

## §17. Currency Snapshot — verified August 2026

**[DURABLE] Most of this document doesn't move.** GoF is 1994, Fowler's *PoEAA* 2002,
Hohpe & Woolf 2003, Evans' *DDD* 2003 — and the forces they describe are unchanged.
Here is what actually shifted.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **The GoF critique** | ⚠️ **Now mainstream rather than contrarian.** 2026 commentary describes a **"post-pattern" turn toward "enlightened simplicity"**, attributed to language maturation, FP, data-oriented design, and cognitive load theory. Counter-position remains live: patterns originated as much in **Smalltalk** (dynamic, first-class functions) as C++, so the "C++ deficiency" story is historically incomplete | Low |
| **Absorbed patterns** | **Iterator, Singleton, Command, Strategy, Template Method** are largely language features or trivial in modern languages. **Modules act as natural singletons in Python and JS.** Frameworks (Spring, .NET, Angular) implement Factory/Proxy/Observer implicitly — **you configure them rather than write them** | Low |
| **Practitioner heuristic** | Widely-repeated 2026 framing: **"Start simple. Add a pattern only when it removes duplication, isolates change, or clarifies intent. If introducing a pattern makes the code harder to explain, it is probably the wrong moment for it."** Composition over inheritance is the settled default | Low |
| **Distributed data patterns** | **Outbox + Saga + CQRS (+ Event Sourcing) is the established production stack** for event-driven microservices. **Debezium/CDC** for log-based publishing. ⚠️ **Dedicated workflow engines (Temporal, Watermill and similar) increasingly preferred over hand-rolled orchestration** | Medium |
| **Saga guidance** | Published heuristic: **choreography for 2–3 steps, orchestration for 4+ or complex logic**. Choreography-plus-Postgres-outbox with a background relay is a common concrete pattern | Medium |
| **⚠️ Event Sourcing caution** | Now widely stated rather than fringe: **event notification covers the majority of cases, CQRS most of the remainder, and Event Sourcing is for the minority where a full audit trail is a hard business requirement.** Documented failure case: a 3-junior team choosing full ES for a profile CRUD — **4 months for what should have taken 2 weeks, undebuggable state-reconstitution bugs, rewritten as REST in 3 weeks** | Low |
| **⚠️ Circuit breaker adoption** | Survey work on microservice deployments found **circuit breaker notably less adopted than API gateway** — roughly half the usage — **which the researchers note weakens resilience** in exactly the systems that need it | Medium |
| **⚠️ Agentic patterns** | **The live, unsettled pattern language.** At least three overlapping taxonomies in circulation (Ng's four, Anthropic's workflow patterns, and emergent reliability/memory patterns from 2025–26). Core distinction — **workflows = predefined code paths; agents = model decides next step** — is stable and useful. Academic work is now presenting FM/agent patterns **in GoF format**. **ReAct predates the current framing by ~2 years.** Multi-agent widely described as a 2023–24 buzzword that is over-applied | **High** |
| **Agentic operational practice** | **Prompts as versioned code**; step-level tracing with token-cost and guardrail-violation metrics (MLflow, LangSmith and similar); **iteration caps as a cost control**; **progressive disclosure against "context rot"** | **High** |

**Goes stale fastest:** §12 → `patterns-llm-agentic-and-legacy-migration` entirely. **Essentially never stale:** §1 → `patterns-foundations-gof-and-alternatives`, §2 → `patterns-foundations-gof-and-alternatives`'s forces
argument, §5 → `patterns-foundations-gof-and-alternatives`, §6.2 → `patterns-architectural`, §9 → `patterns-distributed-concurrency-and-messaging`, §13 → `patterns-llm-agentic-and-legacy-migration`, §14, §15.

---
