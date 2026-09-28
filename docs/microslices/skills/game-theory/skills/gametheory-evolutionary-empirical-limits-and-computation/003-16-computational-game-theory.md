---
id: skill-16-computational-game-theory-4a1fdf389d
purpose: 16 computational game theory
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-evolutionary-empirical-limits-and-computation/SKILL.md
requires: ["skill-15-where-the-theory-fails-empirically-3c77d8944e"]
links: []
---

## §16. Computational Game Theory

**⚠️ Complexity results that constrain how seriously to take equilibrium as a prediction:**
```
Two-player ZERO-SUM Nash    ⚠️ polynomial (linear programming) — easy
General two-player Nash     ⚠️ PPAD-COMPLETE (Daskalakis, Goldberg, Papadimitriou;
                            Chen & Deng) — believed intractable
Correlated equilibrium      ⚠️ polynomial (linear programming) — easy
Optimal Nash (max welfare)  NP-hard
Shapley value               #P-hard in general (§11)
```
> **⚠️ GOTCHA — this is a serious conceptual problem, not a technical footnote.** ⚠️ **If
> computing an equilibrium is intractable, it is hard to argue that players find it.**
> **As Papadimitriou put it, a concept that cannot be computed efficiently is suspect as a
> model of what happens in the world.** **Nash's existence theorem being non-constructive
> (§4.1 → `gametheory-framework-nash-and-classic-games`) turns out to have been a warning.**
>
> ⚠️ **Correlated equilibrium's tractability is the strongest argument in its favour** —
> **and notably, simple no-regret learning dynamics converge to the set of correlated
> equilibria.** **A concept that is both computationally easy and reachable by naive
> learning has a much better claim to describing reality.**

**Algorithmic game theory**: **Price of Anarchy** — ⚠️ **the ratio of worst equilibrium
welfare to optimal welfare.** **Selfish routing on networks has a Price of Anarchy of 4/3
for linear latency (Roughgarden-Tardos)** — ⚠️ **a reassuringly small bound, and the reason
that result is famous.**
**⚠️ Braess's paradox** — **adding a road to a network can make everyone's commute
longer.** **Documented in real road networks, and a direct consequence of equilibrium
routing.**

**⚠️ Practical algorithms that work despite the theory**: **counterfactual regret
minimization (CFR)** solved heads-up limit poker and underlies superhuman no-limit poker
agents; **double oracle** and **PSRO** for large games; **self-play reinforcement
learning**. ⚠️ **Note the pattern: these are no-regret learning methods, not equilibrium
solvers** — **and in two-player zero-sum, no-regret play converges to the minimax value
(§6 → `gametheory-zero-sum-sequential-repeated-and-information`), which is exactly why poker fell and general multi-agent settings are harder.**
