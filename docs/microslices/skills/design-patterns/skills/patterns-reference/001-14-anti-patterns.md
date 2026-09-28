---
id: skill-14-anti-patterns-d930c26b28
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: []
links: ["skill-15-anti-patterns-table-34e43a81d7"]
---

## §14. Anti-Patterns

**[DURABLE] Naming these is at least as valuable as naming the patterns.**

**Structural**: **God object / god class**, **anemic domain model** (⚠️ **data-bags plus a
service layer — arguably the default outcome of layered architecture done carelessly**),
**spaghetti**, **lasagna** (so many layers each adds nothing), **big ball of mud**,
**circular dependencies**, **feature envy**, **shotgun surgery** (one change touches
fifteen files).

**Pattern-specific**: **Singleton abuse** (⚠️ **global mutable state with a design-pattern
name on it** — hostile to testing, hides dependencies, causes ordering bugs), **Service
Locator** (§5 → `patterns-foundations-gof-and-alternatives`), **the Poltergeist** (a class that exists only to call another),
**BaseBean** (inheriting for convenience rather than for an is-a relationship),
**over-abstracted factories**.

**Process**: **premature optimization**, **premature generalization** (⚠️ **"we might need
this later" is the most expensive sentence in software**), **cargo cult architecture**
(⚠️ **adopting Netflix's architecture at 1/10000th of Netflix's scale**), **resume-driven
development**, **the distributed monolith** (⚠️ **microservices that must deploy together —
all the cost, none of the benefit, and the most common microservice failure mode**),
**golden hammer**, **not-invented-here**, **stringly-typed** code, **magic numbers**,
**boat anchor** (dead code kept "just in case"), **feature toggle debt**.

> **⚠️ GOTCHA — pattern over-application, stated plainly, because it is the failure mode
> this whole document exists to prevent.** Symptoms: interfaces with exactly one
> implementation; factories that construct one type; three layers of indirection between
> the caller and the work; class names ending in `Manager`, `Helper`, `Processor`, or
> `AbstractProxyFactoryBean`; **you cannot find where anything actually happens.**
>
> **The asymmetry that should govern your default**: a missing pattern costs you some
> duplication, which you can refactor when the third case appears and you can see the real
> shape. **An unnecessary pattern costs every future reader permanently, and is far harder
> to remove than to add.** When in doubt, don't.

---
