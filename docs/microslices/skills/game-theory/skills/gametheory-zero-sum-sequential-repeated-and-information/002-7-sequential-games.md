---
id: skill-7-sequential-games-08712c42d0
purpose: 7 sequential games
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-zero-sum-sequential-repeated-and-information/SKILL.md
requires: ["skill-6-zero-sum-and-minimax-f1c4ecfd6d"]
links: ["skill-8-repeated-games-d5454f07a3"]
---

## §7. Sequential Games

**Backward induction** — ⚠️ **solve the last decision first, then work back.** In finite
games of perfect information, this yields a **subgame perfect equilibrium**, and
**(Zermelo) every such game is strictly determined.**

**Subgame perfect Nash equilibrium (SPNE, Selten 1965)** — ⚠️ **a Nash equilibrium in
every subgame.** **The purpose is eliminating non-credible threats.**
> **⚠️ GOTCHA — Nash equilibrium permits threats no rational player would carry out.**
> ⚠️ **"If you enter my market I'll price below cost forever" can be part of a Nash
> equilibrium while being irrational to execute.** **Subgame perfection rules it out by
> requiring the threat be optimal at the point it would be used.**
> **⚠️ Which is exactly why commitment devices matter (§5.2 → `gametheory-framework-nash-and-classic-games`): they make an
> otherwise-incredible threat credible by removing your ability not to execute it.**

**⚠️ The chain store paradox (Selten)** shows the limits: **backward induction says the
incumbent should never fight entry in a finite sequence of markets — yet fighting
early to build a reputation seems obviously sensible.** ⚠️ **Resolved by adding incomplete
information about the incumbent's type (§9), and it's a good illustration of backward
induction being logically airtight and behaviourally implausible.**

**Extensions**: **perfect Bayesian equilibrium** and **sequential equilibrium** for
imperfect information — ⚠️ **requiring beliefs at every information set, updated by Bayes'
rule where possible, and specified off-path where it isn't. Off-path beliefs are where the
refinement fights happen.**

---
