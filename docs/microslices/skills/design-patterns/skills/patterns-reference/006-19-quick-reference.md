---
id: skill-19-quick-reference-b094b340c4
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: ["skill-18-the-canon-301417ec6b"]
links: ["skill-20-sources-and-method-d728c97724"]
---

## §19. Quick Reference

### 19.1 Problem → pattern

| Problem | Pattern |
|---|---|
| Their interface doesn't match mine | **Adapter** (§3.2 → `patterns-foundations-gof-and-alternatives`) |
| Complex subsystem, simple need | Facade |
| Layer behaviour composably | **Decorator** / middleware |
| Notify many of a change | Observer / pub-sub |
| Many optional construction params | Builder — ⚠️ **unless your language has named args** |
| Behaviour varies by state | State (explicit machine) |
| Operations over a stable type hierarchy | Visitor — ⚠️ **or pattern matching** (§4 → `patterns-foundations-gof-and-alternatives`) |
| Swap an algorithm | ⚠️ **A function parameter** (§4 → `patterns-foundations-gof-and-alternatives`) |
| Testable business logic | **Hexagonal / ports and adapters** (§6.2 → `patterns-architectural`) |
| Same word, different meanings across the business | **Bounded contexts** (§6.3 → `patterns-architectural`) |
| Integrating a model I don't control | **Anti-Corruption Layer** (§7 → `patterns-architectural`) |
| Write to DB *and* publish an event | ⚠️ **Transactional Outbox** (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Business operation spanning services | **Saga** — choreography ≤3 steps, else orchestration (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Reads and writes have different shapes | CQRS (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Full audit trail is a hard requirement | Event Sourcing — ⚠️ **and only then** (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Duplicate messages | Idempotent consumer / inbox (§8 → `patterns-distributed-concurrency-and-messaging`) |
| Downstream failing, don't cascade | **Circuit breaker** (§9 → `patterns-distributed-concurrency-and-messaging`) |
| Transient failure | Retry with backoff **and jitter** (§9 → `patterns-distributed-concurrency-and-messaging`) |
| One dependency shouldn't consume everything | Bulkhead (§9 → `patterns-distributed-concurrency-and-messaging`) |
| Overloaded | Load shedding — ⚠️ **reject early, don't collapse** (§9 → `patterns-distributed-concurrency-and-messaging`) |
| Replace a legacy system | **Strangler Fig** (§13 → `patterns-llm-agentic-and-legacy-migration`) |
| Change a schema under live traffic | **Expand-contract** (§13 → `patterns-llm-agentic-and-legacy-migration`) |
| Verify a migration | **Parallel run** (§13 → `patterns-llm-agentic-and-legacy-migration`) |
| Multi-step LLM task | ⚠️ **A workflow, not an agent, if you can sequence it** (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| LLM needs current or private data | RAG (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| LLM output quality varies | Evaluator-optimizer with **separated roles** (§12 → `patterns-llm-agentic-and-legacy-migration`) |
| Agent could do something costly | **Human-in-the-loop gate + iteration cap** (§12 → `patterns-llm-agentic-and-legacy-migration`) |

### 19.2 Before adding a pattern
- [ ] What **force** am I resolving? Can I state it in one sentence?
- [ ] Does my language already have this as a feature? (§3 → `patterns-foundations-gof-and-alternatives`, §4 → `patterns-foundations-gof-and-alternatives`)
- [ ] Do I have **two** cases, or am I speculating about the second?
- [ ] Does this **remove duplication, isolate change, or clarify intent**?
- [ ] Would a new team member find the code **easier** to explain, or harder?
- [ ] What does it **cost** — and have I said that out loud?
- [ ] Am I solving a problem, or demonstrating knowledge?

---
