---
id: skill-4-nash-equilibrium-b13656c708
purpose: 4 nash equilibrium
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-framework-nash-and-classic-games/SKILL.md
requires: ["skill-3-dominance-e50d2256fa"]
links: ["skill-5-the-classic-games-6c4d30e2ca"]
---

## §4. Nash Equilibrium

### 4.1 Definition and existence
**⚠️ A strategy profile where no player can improve by unilaterally deviating.** Each
player's strategy is a best response to the others'.

**Nash (1950)**: ⚠️ **every finite game has at least one equilibrium in mixed strategies.**
**The proof is a fixed-point argument (Kakutani/Brouwer)** — ⚠️ **which is why it's
non-constructive, and why §16 → `gametheory-evolutionary-empirical-limits-and-computation`'s complexity results are not a contradiction: existence is
guaranteed, finding it is hard.**

### 4.2 Mixed strategies
**Randomizing over pure strategies.** ⚠️ **The defining property people miss: in a mixed
equilibrium, you are indifferent among all strategies you play with positive
probability.**
> **⚠️ GOTCHA — this produces the most counterintuitive result in basic game theory.**
> ⚠️ **Your equilibrium mixing probabilities are determined by making your OPPONENT
> indifferent, not by optimizing your own payoff.** **Consequence: if a player's payoffs
> change, it is the *other* player's equilibrium mix that shifts, not their own.**
> **This routinely surprises people and it's a good test of whether you've understood
> mixed equilibrium.**

**Interpretations**: deliberate randomization (⚠️ **genuinely correct in poker and
penalty kicks**), **population frequencies** (§14 → `gametheory-evolutionary-empirical-limits-and-computation`), or **beliefs about an opponent's
type** (Harsanyi purification).

### 4.3 ⚠️ What Nash equilibrium is not
- **⚠️ Not necessarily efficient.** The Prisoner's Dilemma's unique equilibrium is Pareto-
  dominated (§5.1). **Equilibrium ≠ good outcome.**
- **⚠️ Not unique.** Most games have many; **selecting among them is an unsolved problem**
  (refinements: subgame perfection §7 → `gametheory-zero-sum-sequential-repeated-and-information`, trembling-hand, risk vs payoff dominance).
- **⚠️ Not a prediction of behaviour** without additional assumptions about how players
  reach it. **The theory says where you'd stop, not how you get there.**
- **⚠️ Not a recommendation.** "Play your Nash strategy" is only advice if you believe
  others will too.

**Correlated equilibrium (Aumann)** — ⚠️ **players observe a shared signal and condition
on it.** **Weaker than Nash, can achieve better payoffs, is computationally easy (§16 → `gametheory-evolutionary-empirical-limits-and-computation`),
and is arguably the more natural concept** — a traffic light is a correlating device.

---
