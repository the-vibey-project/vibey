---
id: skill-9-fine-grained-complexity-b574dcec9d
purpose: 9 fine grained complexity
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-beyond-np-space-and-distributed-limits/SKILL.md
requires: ["skill-8-beyond-np-30e236808e"]
links: ["skill-10-space-and-memory-0e7de93f11"]
---

## §9. Fine-Grained Complexity

**[DURABLE, and under-taught relative to its practical value.]** Classical complexity asks
"polynomial or not." **Fine-grained complexity asks: is my O(n²) algorithm actually
optimal?** — and it answers via **conditional lower bounds**.

**The method**: assume a hardness conjecture, then use **fine-grained reductions** — so
tight that any improvement to the target implies an improvement to the source — to transfer
hardness. **The core conjectures**: **SETH** (the Strong Exponential Time Hypothesis: for
any ε > 0 there's a k such that k-SAT can't be solved in 2^((1-ε)n)), **the Orthogonal
Vectors hypothesis**, **3SUM**, and **APSP**.

**[DURABLE] Why an engineer should care**: it tells you when to stop optimizing.
Well-known results in this line establish, under SETH, that **Edit Distance and Longest
Common Subsequence have no strongly subquadratic algorithm**, that **Orthogonal Vectors
needs n²**, and that **Bellman's classic O(nT) Subset Sum algorithm can't be substantially
improved.** Similar conditional bounds cover graph diameter approximation, dominating set,
and a range of computational-geometry problems.

**⚠️ The engineering translation: if your string-diff is quadratic, that is very likely not
your fault, and no amount of profiling will fix it.** The right move is to change the
problem — restrict the input, exploit structure, approximate, or use a different similarity
measure — not to keep optimizing the constant.

**⚠️ These are conditional results.** If SETH is false the bounds evaporate — but SETH has
survived decades of attack and is treated as a working assumption.

**[VERSIONED] Quantum analogues exist and are active** (§16 → `toc-reference`): SETH itself fails quantumly
because Grover solves CNF-SAT in about 2^(n/2), so researchers built **QSETH** frameworks
to get meaningful quantum conditional lower bounds instead.

---
