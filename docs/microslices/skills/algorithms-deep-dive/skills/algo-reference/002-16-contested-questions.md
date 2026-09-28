---
id: skill-16-contested-questions-cd5eef5285
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-reference/SKILL.md
requires: ["skill-15-anti-patterns-7cb55564be"]
links: ["skill-17-currency-snapshot-verified-august-2026-37e644c50e"]
---

## §16. Contested Questions

**16.1 Is there a universal "best" structure?** No, and the **RUM conjecture** names why:
you can optimize at most two of **R**ead overhead, **U**pdate overhead, and **M**emory
overhead. **The B-tree vs. LSM divide is RUM made concrete** (§5.2 → `algo-data-structures`). Treat any claim of
across-the-board superiority as a signal that the benchmark was narrow.

**16.2 How much should engineers implement vs. use?** *For implementing*: you understand
the failure modes, and standard libraries make general-purpose choices that may be wrong
for your data. *For using*: library implementations are extensively tested, tuned, and
maintained, and **your hand-rolled version will be slower and buggier.** **[CONTESTED] The
position here: implement once to learn, then use the library — and invest your effort in
knowing what the library does rather than in replacing it.**

**16.3 Do interview algorithm questions measure anything?** *For*: they test problem
decomposition, and knowing the toolkit genuinely helps. *Against*: they select for recent
practice on a narrow corpus, correlate poorly with the job, and reward memorization.
**Widely and legitimately contested.**

**16.4 Are learned indexes real?** Replacing index structures with models that predict
position. *For*: strong results on read-only sorted data, real memory savings. *Against*:
updates are hard, worst-case guarantees are weak, and adoption remains limited relative to
the attention. **Genuinely unsettled; treat production claims with skepticism.**

**16.5 Cache-oblivious vs. cache-aware?** Cache-oblivious algorithms achieve good behaviour
at every level of the hierarchy without knowing its parameters — elegant and theoretically
lovely. **Cache-aware tuning usually wins in practice when you know your target**, at the
cost of portability.

**16.6 SIMD vs. ILP?** ⚠️ **A live design question, not a settled one.** Rust's new sorts
deliberately **chose instruction-level parallelism over SIMD**, on the grounds that ILP
adapts across architectures and data types while SIMD depends on specific vector
instruction sets. Others take the opposite view for fixed workloads on known hardware.
**The trade-off is genuinely portability vs. peak.**

**16.7 Do theoretical hash-table results matter to practitioners?** §4.3 → `algo-data-structures`. **The honest
answer: rarely and indirectly** — but the reason to care is that "settled for 40 years"
turned out not to mean "settled."

---
