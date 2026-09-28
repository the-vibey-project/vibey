---
id: skill-18-the-canon-301417ec6b
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-2f9cef220e"]
links: ["skill-19-quick-reference-b094b340c4"]
---

## §18. The Canon

### 18.1 Books

| Author | Work | Why |
|---|---|---|
| **Gamma, Helm, Johnson & Vlissides** | ***Design Patterns*** (1994) | The original. ⚠️ **Read with §2 → `patterns-foundations-gof-and-alternatives` in hand** — it's a historical document with durable content, not a manual |
| **Fowler** | ***Patterns of Enterprise Application Architecture*** (2002) | ⚠️ **Arguably more useful than GoF for most working engineers.** Repository, Unit of Work, Active Record, Data Mapper |
| **Fowler** | *Refactoring* (2nd ed.) | The other half — how to get *to* a design, not just name it |
| **Hohpe & Woolf** | ***Enterprise Integration Patterns*** (2003) | §11 → `patterns-distributed-concurrency-and-messaging`, and **the vocabulary is still standard 20+ years on** |
| **Evans** | ***Domain-Driven Design*** (2003) | Dense. **Read Vernon's *Implementing DDD* or *DDD Distilled* first** |
| **Nygard** | ***Release It!*** (2nd ed.) | ⚠️ **§9 → `patterns-distributed-concurrency-and-messaging`'s source, and the best book on production failure modes.** If you read one book here, consider this one |
| **Richardson** | *Microservices Patterns* | §7–§8 → `patterns-architectural`, `patterns-distributed-concurrency-and-messaging`, and **microservices.io** is the free companion catalogue |
| **Kleppmann** | *Designing Data-Intensive Applications* | The forces underneath §8 → `patterns-distributed-concurrency-and-messaging` |
| **Newman** | *Building Microservices*; *Monolith to Microservices* | §7 → `patterns-architectural` and §13 → `patterns-llm-agentic-and-legacy-migration` |
| **Feathers** | *Working Effectively with Legacy Code* | §13 → `patterns-llm-agentic-and-legacy-migration`, and still unmatched |
| **Freeman & Robson** | *Head First Design Patterns* | **The most approachable way in.** Updated for modern Java |
| **Ramalho** | *Fluent Python* | ⚠️ **Ch. 10, "Design Patterns with First-Class Functions," is the single best demonstration of §4 → `patterns-foundations-gof-and-alternatives`'s argument** |
| **Hunt & Thomas** | *The Pragmatic Programmer* | The judgment layer around all of it |
| **Alexander** | *A Pattern Language* | Where the whole idea came from. Architecture, not software |

### 18.2 Sites and people
**refactoring.guru** (the best free pattern catalogue — clear diagrams, multi-language),
**python-patterns.guide** (⚠️ **the sharpest published critique of GoF-in-a-modern-language**),
**martinfowler.com** (bliki — the reference for most of this vocabulary),
**microservices.io** (Chris Richardson's free catalogue for §7–§8 → `patterns-architectural`, `patterns-distributed-concurrency-and-messaging`),
**Microsoft's Cloud Design Patterns** and **AWS Prescriptive Guidance** (solid, vendor-shaped),
**c2.com wiki** (where the patterns community argued it out originally — still worth reading).

**People**: **Martin Fowler**, **Kent Beck**, **Michael Nygard**, **Gregor Hohpe**,
**Eric Evans** and **Vaughn Vernon**, **Sam Newman**, **Chris Richardson**,
**Rich Hickey** (*Simple Made Easy* — ⚠️ **the best single talk on why simplicity beats
familiarity**), **Sandi Metz** (OO design, and unusually good on when *not* to abstract),
**Kevlin Henney**, **Ralph Johnson** (§1 → `patterns-foundations-gof-and-alternatives`'s quote).

---
