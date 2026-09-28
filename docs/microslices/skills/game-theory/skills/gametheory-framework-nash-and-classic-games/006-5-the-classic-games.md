---
id: skill-5-the-classic-games-6c4d30e2ca
purpose: 5 the classic games
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-framework-nash-and-classic-games/SKILL.md
requires: ["skill-4-nash-equilibrium-b13656c708"]
links: []
---

## §5. The Classic Games

### 5.1 Prisoner's Dilemma
```
              Cooperate   Defect
Cooperate       3, 3       0, 5
Defect          5, 0       1, 1        ⚠️ unique equilibrium: (Defect, Defect)
```
**⚠️ Defection strictly dominates**, so the equilibrium is unique and Pareto-dominated.
**Individual rationality produces a collectively worse outcome — the canonical statement
that these can conflict.**
> **⚠️ GOTCHA — the Prisoner's Dilemma is enormously over-applied, and the specific error
> is diagnosable.** ⚠️ **It requires `T > R > P > S` AND `2R > T + S`.** **Most real
> situations labelled "a prisoner's dilemma" are actually Stag Hunt (§5.2 — a coordination
> problem with a *good* equilibrium available) or Chicken.**
> **The distinction is not pedantic: a coordination failure needs communication and trust;
> a true PD needs enforcement or repetition** (§8 → `gametheory-zero-sum-sequential-repeated-and-information`). ⚠️ **Prescribing the wrong remedy
> follows directly from misdiagnosing the game.**

### 5.2 The other four you need
```
STAG HUNT (assurance)        Two equilibria: (Stag,Stag) payoff-dominant,
                             (Hare,Hare) risk-dominant. ⚠️ A TRUST problem, not a
                             greed problem — the good outcome IS an equilibrium

CHICKEN (hawk-dove)          Two asymmetric pure equilibria + a mixed one.
                             ⚠️ Commitment wins: visibly removing your own options
                             (throwing away the steering wheel) is a strategic ADVANTAGE

BATTLE OF THE SEXES          Coordination with conflicting preferences.
                             ⚠️ Both want to coordinate; they disagree on where

MATCHING PENNIES             ⚠️ Zero-sum, NO pure equilibrium, unique mixed equilibrium
                             at 50/50. The archetype for §6
```
**⚠️ Commitment as advantage (Schelling) is the deep idea in Chicken**: **in strategic
settings, reducing your own options can improve your outcome** — burning bridges, binding
contracts, publicly irreversible positions. ⚠️ **This inverts the decision-theoretic
intuition that more options are always weakly better, and the inversion is real.**
