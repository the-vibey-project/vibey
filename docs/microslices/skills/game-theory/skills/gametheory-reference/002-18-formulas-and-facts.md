---
id: skill-18-formulas-and-facts-39cc1816e4
purpose: 18 formulas and facts
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-reference/SKILL.md
requires: ["skill-17-misconceptions-61db452df3"]
links: ["skill-19-books-e90aa8d8b5"]
---

## §18. Formulas and Facts

```
NASH EQUILIBRIUM
sᵢ* ∈ argmax uᵢ(sᵢ, s₋ᵢ*)  for all i
⚠️ Every finite game has a mixed equilibrium (Nash 1950, via fixed point)
⚠️ Mixed equilibrium: you are indifferent over your support

ZERO-SUM
⚠️ max min = min max (von Neumann 1928); solvable by LP

REPEATED GAMES
Cooperation sustainable when δ ≥ (T−R)/(T−P)   [grim trigger, PD]
⚠️ Folk theorem: any individually rational feasible payoff, for δ high enough

BARGAINING
Nash solution: max (u₁−d₁)(u₂−d₂)
⚠️ Rubinstein: more patient player gets more

COOPERATIVE
Shapley: φᵢ = Σ_S [|S|!(n−|S|−1)!/n!] · [v(S∪{i}) − v(S)]
⚠️ = average marginal contribution over arrival orders

AUCTIONS
⚠️ Second-price: bid your true value (dominant)
First-price: shade below value
⚠️ Revenue equivalence under private/independent values, risk neutrality, symmetry

COMPLEXITY ⚠️
Zero-sum Nash: P · General Nash: PPAD-complete
Correlated equilibrium: P · Shapley value: #P-hard
Price of Anarchy, selfish routing with linear latency: 4/3

EVOLUTIONARY
Replicator: ẋᵢ = xᵢ(fᵢ − f̄)
⚠️ ESS ⟹ Nash, but not conversely

EXPERIMENTAL ⚠️
Ultimatum: modal offers ~40–50%; offers <20% often rejected
p-beauty contest: equilibrium 0; observed 1–3 levels of reasoning
```

---
