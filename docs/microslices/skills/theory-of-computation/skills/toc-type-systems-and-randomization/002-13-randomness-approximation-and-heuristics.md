---
id: skill-13-randomness-approximation-and-heuristics-139de28a6c
purpose: 13 randomness approximation and heuristics
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-type-systems-and-randomization/SKILL.md
requires: ["skill-12-type-systems-logic-and-verification-4d5ccab59a"]
links: []
---

## §13. Randomness, Approximation, and Heuristics

**Randomized complexity**: **BPP** (bounded-error probabilistic polynomial time) — and
**[DURABLE] it is now widely conjectured that P = BPP**, i.e. randomness probably doesn't
buy asymptotic power, which was a genuine surprise. **Randomness buys simplicity and
practical speed**, which is why randomized algorithms are everywhere: quicksort's pivot,
Miller–Rabin primality, hashing, Monte Carlo methods, randomized load balancing.

**⚠️ Monte Carlo vs. Las Vegas** is worth keeping straight: Monte Carlo is fast with a
bounded error probability; Las Vegas is always correct with randomized runtime. **You need
to know which one you're deploying**, because "wrong 1 in 2^40 times" is a very different
operational posture from "occasionally slow."

**Approximation** (§6.2 → `toc-computability-and-complexity`), and the sharp edge: **the PCP theorem** implies many problems are
**hard even to approximate well** — so "just approximate it" is not universally available,
and for some problems the achievable ratio is provably capped unless P = NP.

**Heuristics and metaheuristics** — greedy, local search, simulated annealing, tabu search,
genetic algorithms, beam search. **[DURABLE] No performance guarantees, frequently
excellent in practice**, and **the No Free Lunch theorem** says no optimizer beats all
others across all problems — which is the formal version of "your heuristic works because
it exploits structure in your instances," and a reason to be suspicious of anyone selling a
universal optimizer.
