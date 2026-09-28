---
id: skill-1-the-framework-075795fe51
purpose: 1 the framework
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-framework-nash-and-classic-games/SKILL.md
requires: ["skill-0-routing-57b8a38227"]
links: ["skill-2-representations-261d2c5048"]
---

## §1. The Framework

### 1.1 What defines a game
```
Players        who decides
Strategies     ⚠️ a COMPLETE contingent plan — what to do at every point you might act
Payoffs        utility over outcomes
Information    who knows what, when
Timing         simultaneous or sequential
```
**⚠️ "Strategy" is a technical term and it trips people up**: it is not a single move. **In
chess, a strategy specifies your response to every possible position** — an astronomically
large object. **This matters because equilibrium is defined over strategies, not moves.**

**Common knowledge** — ⚠️ **everyone knows X, everyone knows everyone knows X, ad
infinitum.** **This is far stronger than "everyone knows"** and it does real work in the
theory (§18 → `gametheory-reference`'s electronic mail game).

### 1.2 ⚠️ What "rational" actually assumes
**A rational player has a complete, transitive preference ordering and maximizes expected
utility with respect to it** (von Neumann-Morgenstern, 1944, from four axioms:
completeness, transitivity, continuity, independence).

> **⚠️ GOTCHA — this is the most misunderstood point in the subject.**
> ⚠️ **Rationality does NOT mean selfish, money-maximizing, cold, or unemotional.** **A
> player whose utility function values their child's welfare above their own is rational.
> A player who derives utility from punishing unfairness is rational.**
> **The assumption is *consistency*, not *content*.**
>
> ⚠️ **The real limitation is different and worth stating precisely**: the theory assumes
> **unlimited computational ability**, **correct beliefs about others' payoffs**, and
> **common knowledge of rationality.** **Those are the assumptions that actually fail**
> (§15 → `gametheory-evolutionary-empirical-limits-and-computation`, §16 → `gametheory-evolutionary-empirical-limits-and-computation`).

**⚠️ Utility is ordinal in preference and cardinal only up to positive affine
transformation.** **Interpersonal comparison of utility is not licensed by the
framework** — which is why §11 → `gametheory-bargaining-cooperative-mechanism-design-and-matching` and §12 → `gametheory-bargaining-cooperative-mechanism-design-and-matching` have to work hard to say anything about fairness.

---
