---
id: skill-5-complexity-classes-a018974ce3
purpose: 5 complexity classes
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-computability-and-complexity/SKILL.md
requires: ["skill-4-computability-what-you-cannot-do-c1d36c8bf6"]
links: ["skill-6-your-problem-is-np-hard-now-what-26f15bc1fa"]
---

## §5. Complexity Classes

### 5.1 The map

```
    P  ⊆  NP  ⊆  PSPACE  ⊆  EXPTIME
    │      │       │
    │      │       └── games, quantified formulas, some planning
    │      └────────── verifiable in poly time (SAT, TSP-decision, scheduling…)
    └───────────────── solvable in poly time
    
  ⚠️ We know P ≠ EXPTIME (time hierarchy theorem).
     We do NOT know whether P = NP, NP = PSPACE, or P = PSPACE.
```

**[DURABLE] The definition of NP that actually helps engineers**: not "solvable by a
nondeterministic machine" but **"a proposed solution can be checked quickly."** If someone
hands you an assignment, can you verify it in polynomial time? Then it's in NP. **That
framing makes NP-membership obvious for most problems you'll meet.**

**NP-hard**: at least as hard as everything in NP. **NP-complete**: in NP *and* NP-hard —
the hardest problems in NP, all equivalent under polynomial reduction.
**⚠️ NP-hard problems need not be in NP** — optimization versions and problems outside NP
are often NP-hard without being NP-complete, and the distinction matters when someone
claims a "solution."

**co-NP** contains problems whose *no*-instances are easily verified. **Tautology checking
is co-NP-complete** — which is why proving a formula always true is structurally harder to
certify than finding a counterexample.

### 5.2 Some honest cautions

**⚠️ Polynomial ≠ fast.** An O(n¹⁰⁰) algorithm is polynomial and useless. Galactic
algorithms with enormous constants are polynomial and never run. **P is a robust
theoretical boundary, not a promise about your latency budget.**

**⚠️ Asymptotics hide constants and cache behaviour.** For real n, an O(n log n) algorithm
with terrible locality routinely loses to an O(n²) one that fits in cache. **Measure**
(§9 → `toc-beyond-np-space-and-distributed-limits` makes this precise in the other direction).

**⚠️ Worst case ≠ your case.** Quicksort is O(n²) worst case and the practical default.
Simplex is exponential worst case and dominates linear programming in practice.
**This gap is the entire subject of §6.3.**

---
