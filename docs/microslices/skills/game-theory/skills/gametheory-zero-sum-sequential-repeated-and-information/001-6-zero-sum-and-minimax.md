---
id: skill-6-zero-sum-and-minimax-f1c4ecfd6d
purpose: 6 zero sum and minimax
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-zero-sum-sequential-repeated-and-information/SKILL.md
requires: []
links: ["skill-7-sequential-games-08712c42d0"]
---

## §6. Zero-Sum and Minimax

**⚠️ Strictly competitive: one player's gain is exactly the other's loss.**
**von Neumann's minimax theorem (1928)** — ⚠️ **every finite two-player zero-sum game has a
value, and optimal mixed strategies exist.** `max min = min max`.
**⚠️ This is far stronger than Nash equilibrium in general games**: the value is unique,
all equilibria are interchangeable and give the same payoff, and **the equilibrium strategy
is a genuine guarantee — a security level you can achieve regardless of what your opponent
does.** ⚠️ **In non-zero-sum games no such guarantee exists.**

**⚠️ Solvable as a linear program**, which is why zero-sum games are computationally easy
and general games are not (§16 → `gametheory-evolutionary-empirical-limits-and-computation`).

> **⚠️ GOTCHA — most real situations are not zero-sum, and calling them so is a
> consequential error.** ⚠️ **Trade, negotiation, and most business competition have
> gains from cooperation available.** **"Zero-sum thinking" as a cognitive bias is
> precisely the misapplication of this model**, and it forecloses the integrative
> solutions §10 → `gametheory-bargaining-cooperative-mechanism-design-and-matching` exists to find.

---
