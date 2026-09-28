---
id: skill-20-quick-reference-88a22130fc
purpose: 20 quick reference
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-reference/SKILL.md
requires: ["skill-19-books-e90aa8d8b5"]
links: ["skill-21-method-a3178b372a"]
---

## §20. Quick Reference

### 20.1 Picker
| Situation | Tool |
|---|---|
| Simultaneous, complete information | **Nash equilibrium; check dominance first** (§3 → `gametheory-framework-nash-and-classic-games`, §4 → `gametheory-framework-nash-and-classic-games`) |
| Strictly competitive | ⚠️ **Minimax — you get a genuine guarantee** (§6 → `gametheory-zero-sum-sequential-repeated-and-information`) |
| Sequential, perfect information | **Backward induction → SPNE** (§7 → `gametheory-zero-sum-sequential-repeated-and-information`) |
| Non-credible threats in the solution | ⚠️ **Apply subgame perfection** (§7 → `gametheory-zero-sum-sequential-repeated-and-information`) |
| Ongoing relationship | ⚠️ **Repeated game; check the discount factor** (§8 → `gametheory-zero-sum-sequential-repeated-and-information`) |
| Asymmetric information about types | **Bayesian game; signalling or screening** (§9 → `gametheory-zero-sum-sequential-repeated-and-information`) |
| Splitting a surplus | **Nash bargaining or Rubinstein; ⚠️ improve your BATNA** (§10 → `gametheory-bargaining-cooperative-mechanism-design-and-matching`) |
| Allocating joint costs or credit | ⚠️ **Shapley value** (§11 → `gametheory-bargaining-cooperative-mechanism-design-and-matching`) |
| Designing rules for self-interested agents | **Mechanism design; ⚠️ check the impossibility theorems first** (§12 → `gametheory-bargaining-cooperative-mechanism-design-and-matching`) |
| Selling a single item | **Second-price for truthfulness; ⚠️ check revenue-equivalence assumptions** (§12 → `gametheory-bargaining-cooperative-mechanism-design-and-matching`) |
| Two-sided allocation without prices | ⚠️ **Deferred acceptance; decide who proposes** (§13 → `gametheory-bargaining-cooperative-mechanism-design-and-matching`) |
| Populations without deliberation | **Replicator dynamics, ESS** (§14 → `gametheory-evolutionary-empirical-limits-and-computation`) |
| Predicting real human play | ⚠️ **QRE, level-k — not plain Nash** (§15 → `gametheory-evolutionary-empirical-limits-and-computation`) |
| Solving a large game computationally | ⚠️ **No-regret learning (CFR), not equilibrium solvers** (§16 → `gametheory-evolutionary-empirical-limits-and-computation`) |

### 20.2 Modelling checklist
- [ ] Who are the players, and is the relevant set actually larger? (§1 → `gametheory-framework-nash-and-classic-games`)
- [ ] Are strategies complete contingent plans, or am I listing moves? (§1.1 → `gametheory-framework-nash-and-classic-games`)
- [ ] Are payoffs *utilities*, including non-monetary concerns? (§1.2 → `gametheory-framework-nash-and-classic-games`)
- [ ] Perfect vs complete information — which am I assuming? (§2 → `gametheory-framework-nash-and-classic-games`)
- [ ] Is this genuinely a PD, or a coordination game? ⚠️ **Check the inequalities** (§5.1 → `gametheory-framework-nash-and-classic-games`)
- [ ] One-shot or repeated, and is the horizon known? (§8 → `gametheory-zero-sum-sequential-repeated-and-information`)
- [ ] Does my solution rely on a non-credible threat? (§7 → `gametheory-zero-sum-sequential-repeated-and-information`)
- [ ] Is the equilibrium unique — and if not, what selects among them? (§4.3 → `gametheory-framework-nash-and-classic-games`)
- [ ] Would real people play this way? (§15 → `gametheory-evolutionary-empirical-limits-and-computation`)
- [ ] Could the players actually compute this? (§16 → `gametheory-evolutionary-empirical-limits-and-computation`)

---
