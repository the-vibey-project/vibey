---
id: skill-16-contested-questions-c66c5dfb07
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: ["skill-15-anti-patterns-table-34e43a81d7"]
links: ["skill-17-currency-snapshot-verified-august-2026-2f9cef220e"]
---

## §16. Contested Questions

**16.1 Are GoF patterns obsolete?** §2 → `patterns-foundations-gof-and-alternatives` in full. **[CONTESTED, genuinely.** The "patterns
are C++ deficiencies" claim is historically shaky given the Smalltalk origins; the
"patterns are timeless" claim under-weights how much modern languages absorbed. **The
defensible position is per-pattern, not wholesale** — §3 → `patterns-foundations-gof-and-alternatives` audits them individually.]

**16.2 Do patterns help or hurt juniors?** *Help*: shared vocabulary, exposure to
considered designs, a path past reinventing. *Hurt*: **encourages installing patterns
rather than solving problems**, and pattern-recognition becomes a proxy for judgment.
**The teaching order that seems to work: forces first, then patterns as named responses,
and never the catalogue first.**

**16.3 OOP vs. functional vs. data-oriented?** All three have real domains. **The
industry has broadly moved toward composition over inheritance, immutability by default,
and functions as first-class**, without abandoning objects. **⚠️ Treat strong advocacy in
any direction as a signal of narrow exposure.**

**16.4 Is Clean Architecture worth its cost?** *For*: testability, replaceable
infrastructure, findable business logic. *Against*: **file-count explosion, indirection,
and genuine overkill for thin-domain applications.** Much of the criticism is really
criticism of applying it uniformly rather than of the idea.

**16.5 Microservices — solved question or ongoing mistake?** The pendulum has swung toward
modular monoliths, and **"microservices are an organizational solution adopted for
technical-sounding reasons"** is now a mainstream position rather than a contrarian one.
Still genuinely right at sufficient organizational scale.

**16.6 Is Event Sourcing worth it?** *For*: complete audit trail, temporal queries,
debugging by replay, and in some regulated domains it's a requirement. *Against*: §8 → `patterns-distributed-concurrency-and-messaging`'s
cautionary case is representative rather than exceptional. **[CONTESTED, but the evidence
leans toward "less often than practitioners think."]**

**16.7 Are the agentic patterns real patterns or vendor framing?** ⚠️ **Genuinely
unresolved and worth holding loosely.** Some — workflow-vs-agent, human-in-the-loop,
evaluator-optimizer, guardrails — describe forces that clearly recur. Others are framework
marketing with a pattern name attached. **Multiple competing taxonomies is what an
immature pattern language looks like**, and this one is two to three years old against
GoF's decade of prior art.

---
