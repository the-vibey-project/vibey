---
id: skill-11-cooperative-game-theory-67e7a68c7b
purpose: 11 cooperative game theory
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-bargaining-cooperative-mechanism-design-and-matching/SKILL.md
requires: ["skill-10-bargaining-5af17d095b"]
links: ["skill-12-mechanism-design-and-auctions-0de48cdb19"]
---

## §11. Cooperative Game Theory

**⚠️ Different question entirely: assume binding agreements are possible, and ask how to
divide the gains.** **The primitive is the characteristic function `v(S)` — what each
coalition can guarantee itself.**

**The Core** — allocations no coalition can improve on by defecting. ⚠️ **May be empty**
(⚠️ **an empty core means the grand coalition is inherently unstable — a genuinely useful
diagnostic**) **and may be large.**

**Shapley value** — ⚠️ **the unique allocation satisfying efficiency, symmetry, null
player, and additivity.** **Computed as each player's average marginal contribution over
all orderings of arrival.**
⚠️ **It always exists and is unique — unlike the core — which is why it's the standard
tool for cost allocation, and why it has been adopted in machine learning as SHAP for
feature attribution.** **The same axioms, a different application.**
**⚠️ Computing it exactly is exponential in the number of players; sampling approximations
are standard.**

**Also**: **nucleolus**, **bargaining set**, **Banzhaf power index** (⚠️ **for voting
power — and it shows that voting weight and voting power diverge sharply; a party with 49%
of votes may have the same power as one with 26%**).

---
