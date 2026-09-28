---
id: skill-3-dominance-e50d2256fa
purpose: 3 dominance
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-framework-nash-and-classic-games/SKILL.md
requires: ["skill-2-representations-261d2c5048"]
links: ["skill-4-nash-equilibrium-b13656c708"]
---

## §3. Dominance

**Strictly dominated** — worse than another strategy against *every* opponent profile.
⚠️ **A rational player never plays one, so you can delete it — and iterated elimination of
strictly dominated strategies is order-independent.**
**Weakly dominated** — never better, sometimes worse. ⚠️ **Iterated elimination of *weakly*
dominated strategies IS order-dependent, and can eliminate legitimate equilibria. Handle
with care.**

**Dominant strategy equilibrium** — everyone has a single best strategy regardless of
others. ⚠️ **Rare and extremely strong when it exists** — it needs no beliefs about others
at all, which is exactly why §12 → `gametheory-bargaining-cooperative-mechanism-design-and-matching` prizes dominant-strategy mechanisms.

**Rationalizability** — ⚠️ **the weaker solution concept: strategies surviving iterated
elimination of never-best-responses.** **Every Nash equilibrium is rationalizable; the
converse fails.**

---
