---
id: skill-1-choosing-b2a655545d
purpose: 1 choosing
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-foundations-and-machine-model/SKILL.md
requires: ["skill-0-routing-76d3272140"]
links: ["skill-2-the-machine-you-are-actually-programming-5042ea6ca7"]
---

## §1. Choosing

**[DURABLE] The questions that determine the answer, in order:**

1. **What operations, at what ratio?** A structure optimized for reads is usually bad at
   writes. **Write down the operation mix before choosing** — "we insert once and query a
   million times" and "we update constantly" have opposite answers.
2. **How much data, and where does it live?** L1 / L2 / L3 / RAM / SSD / network. **The
   answer changes completely at each boundary** (§2.1), and this is the question most
   often skipped.
3. **What does the data look like?** Sorted? Nearly sorted? Skewed? Many duplicates?
   Adversarial? **Real data has structure and the best algorithms exploit it** (§7.2 → `algo-core-algorithms`).
4. **What are the ordering and locality requirements?** Do you need range scans, or only
   point lookups? That single question decides hash vs. tree (§4 → `algo-data-structures` vs. §5 → `algo-data-structures`).
5. **What's the tolerance for approximation?** Exact answers are often far more expensive
   than 99%-accurate ones (§12 → `algo-probabilistic-concurrency-and-measurement`).
6. **Is it concurrent?** Changes everything (§14 → `algo-probabilistic-concurrency-and-measurement`).
7. **What's the worst case, and does it matter?** Amortized-good-worst-case-terrible is
   fine for a batch job and unacceptable for a p99 latency SLO (§11.4 → `algo-core-algorithms`).

**[DURABLE] The default answer is usually "an array or a hash map."** Reach for something
exotic only when profiling shows you need it, and be aware that most exotic structures
lose to a flat array below a few thousand elements because of §2.

---
