---
id: skill-28-numbers-f2602bb9ec
purpose: 28 numbers
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-reference/SKILL.md
requires: ["skill-27-misconceptions-5ee43cf33f"]
links: ["skill-29-books-53af209527"]
---

## §28. Numbers

```
⚠️ MIP gap to aim for in production      1–3% is usually plenty
⚠️ Nearest-neighbour TSP quality         ~25% above optimal — starting point only
⚠️ Christofides guarantee                1.5× optimal (metric TSP)
⚠️ First-Fit Decreasing (bin packing)    within 11/9 of optimal
Held-Karp exact TSP                      O(n²2ⁿ) — practical to ~20 nodes
⚠️ Distance matrix size                  n². 1,000 stops → 10⁶ entries
⚠️ Safety stock                          ≈ z · σ over lead time (scales √t)
⚠️ Risk pooling benefit                  safety stock scales ~√n
⚠️ Newsvendor optimal service level      Cu / (Cu + Co)
⚠️ Travel share of manual picking        commonly ~50% of picker time
⚠️ HiGHS vs top commercial (Mittelmann)  ~20× slower (§25.1)
⚠️ Quantum annealer practical limit      a few hundred variables (§25.2)
⚠️ Circuit-model QC testable limit       ~30 binary variables (§25.2)
⚠️ ALOHA-style channel efficiency         (see a radio reference §13 — the same
   "simple protocol collapses under load" lesson applies to dispatch systems)
```

---
