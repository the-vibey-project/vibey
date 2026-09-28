---
id: skill-10-space-and-memory-0e7de93f11
purpose: 10 space and memory
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-beyond-np-space-and-distributed-limits/SKILL.md
requires: ["skill-9-fine-grained-complexity-b574dcec9d"]
links: ["skill-11-distributed-computing-impossibility-results-9e7cb01903"]
---

## §10. Space and Memory

**[DURABLE] Space is the resource engineers under-model.** The classes: **L** (logarithmic
space — you can hold a constant number of pointers, not a copy of the input), **NL**,
**PSPACE**.

**Two results worth carrying:**
- **Savitch's theorem**: NSPACE(f) ⊆ SPACE(f²) — **nondeterminism buys you much less in
  space than in time.**
- **Reingold's theorem** (2005): **undirected s-t connectivity is in log space** — a
  genuinely surprising result, and the directed case remains the standing open challenge.

**[DURABLE] Streaming and sublinear algorithms are the applied face of space complexity**,
and they're everywhere in production infrastructure: **HyperLogLog** (cardinality in
kilobytes), **Count-Min Sketch** (frequency estimation), **Bloom filters** (membership with
one-sided error), **reservoir sampling**. **If you have a "count distinct over a firehose"
problem, the theory already solved it** — and the solution trades exactness for a bounded
error you choose.

**[VERSIONED — the one genuinely major recent theorem in this document.]** In **February
2025, Ryan Williams proved TIME[t] ⊆ SPACE[√(t log t)]** — every multitape Turing machine
running in time t can be simulated in **O(√(t log t))** space. This replaced the
**Hopcroft–Paul–Valiant bound of t/log t that had stood since 1975**, a near-quadratic
improvement described in the field as "an earthquake of a result" and "a true classic
complexity theorem." The proof reduces time-t computation to **Tree Evaluation** and
applies the **Cook–Mertz** space-efficient algorithm from the catalytic-computing line.

**⚠️ Read this correctly.** It is a **space** simulation — **it does not preserve the time
bound**, so it is not an algorithm you deploy tomorrow. **Its significance is theoretical**:
it is a real step toward separating **P from PSPACE**, and it demolished a decades-old
belief about what was possible. **The engineering-adjacent lesson is epistemic**: a
50-year-old "obvious barrier" fell, which is worth remembering whenever someone says
something is known to be impossible when what they mean is that nobody has done it.

---
