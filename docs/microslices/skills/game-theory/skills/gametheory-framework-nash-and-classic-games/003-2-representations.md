---
id: skill-2-representations-261d2c5048
purpose: 2 representations
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-framework-nash-and-classic-games/SKILL.md
requires: ["skill-1-the-framework-075795fe51"]
links: ["skill-3-dominance-e50d2256fa"]
---

## §2. Representations

**Normal (strategic) form** — a payoff matrix; assumes simultaneous choice.
**Extensive form** — a game tree with nodes, branches, and **information sets** (⚠️ **a set
of nodes a player cannot distinguish between — this is how you represent imperfect
information, and a simultaneous game is just a tree with a big information set**).

**⚠️ Perfect vs complete information — routinely confused:**
- **Perfect information**: every player knows the full history when they move. ⚠️ **Chess
  has it; poker does not.**
- **Complete information**: everyone knows everyone's payoff functions. ⚠️ **An auction
  with private valuations lacks it.**
**They are independent.** **§7 → `gametheory-zero-sum-sequential-repeated-and-information` handles imperfect; §9 → `gametheory-zero-sum-sequential-repeated-and-information` handles incomplete.**

---
