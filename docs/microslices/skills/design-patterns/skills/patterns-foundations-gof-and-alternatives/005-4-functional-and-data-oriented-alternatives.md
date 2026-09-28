---
id: skill-4-functional-and-data-oriented-alternatives-2d0b55ce92
purpose: 4 functional and data oriented alternatives
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-foundations-gof-and-alternatives/SKILL.md
requires: ["skill-3-the-gof-audit-52facdaa30"]
links: ["skill-5-dependency-injection-and-inversion-71ff27d785"]
---

## §4. Functional and Data-Oriented Alternatives

**[DURABLE] Many OO patterns have a functional counterpart that is smaller and often
clearer**, and knowing the mapping is more useful than knowing either list alone.

| OO pattern | Functional equivalent |
|---|---|
| Strategy | A function parameter |
| Command | A closure |
| Template Method | A higher-order function |
| Decorator | Function composition |
| Observer | Streams / signals / reactive sequences |
| Visitor | **Pattern matching over a sum type** |
| Factory | A function returning a value |
| Null Object | `Option` / `Maybe` |
| Singleton | A module |

**The functional patterns proper**: **immutability by default** (removes whole categories
of bug), **pure core / imperative shell** (⚠️ **one of the highest-value structural ideas
available** — put logic in pure functions, push I/O to the edges, and testing becomes
trivial), **algebraic data types + exhaustive pattern matching** (the compiler enforces
that you handled every case), **`Result`/`Either` for errors** as values rather than
control flow, **persistent data structures**, and **the monadic patterns** (⚠️ useful
concepts, and **the terminology is a genuine barrier that the community often
underestimates**).

**Data-oriented design** inverts the OO framing entirely: **model the data and its
transformations, not the objects.** Struct-of-arrays layouts, separating data from
behaviour, entity-component systems. **⚠️ It's a serious alternative in performance-critical
domains, not a stylistic preference** — for the hardware reasons, see an algorithms
reference on memory layout.

---
