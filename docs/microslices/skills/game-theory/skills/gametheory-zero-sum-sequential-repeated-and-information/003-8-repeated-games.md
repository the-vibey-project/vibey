---
id: skill-8-repeated-games-d5454f07a3
purpose: 8 repeated games
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-zero-sum-sequential-repeated-and-information/SKILL.md
requires: ["skill-7-sequential-games-08712c42d0"]
links: ["skill-9-incomplete-information-ff86740fbd"]
---

## §8. Repeated Games

**⚠️ Repetition changes everything, because future punishment can sustain present
cooperation.**

**Finitely repeated with a known end** — ⚠️ **backward induction unravels cooperation
completely**: defect in the last round, so defect in the second-last, all the way back.
**The unravelling argument is why "known finite horizon" is such a destructive
assumption.**

**Infinitely repeated (or indefinite horizon)** — ⚠️ **and note the key modelling move:
"infinite" is best read as "the game continues with probability δ each period," which is
just discounting.**
**⚠️ The Folk Theorem**: **for a sufficiently high discount factor, ANY payoff profile
that is individually rational and feasible can be sustained as a subgame perfect
equilibrium.**
> **⚠️ GOTCHA — the folk theorem is usually presented as good news and it is mostly bad
> news for the theory.** ⚠️ **"Anything can happen in equilibrium" means the equilibrium
> concept has almost no predictive power in repeated settings.** **It explains how
> cooperation *can* be sustained; it cannot tell you whether it *will* be.**

**Strategies**: **Grim trigger** (⚠️ **cooperate until any defection, then defect
forever — maximally harsh, and unforgiving of noise**), **Tit-for-tat**, **Tit-for-two-tats**,
**Win-stay-lose-shift (Pavlov)**.
**⚠️ Axelrod's tournaments (1980s)** found tit-for-tat successful and identified the
properties that mattered: **nice** (never defect first), **retaliatory**, **forgiving**,
**clear**.
⚠️ **The important caveat, and it's often dropped: tit-for-tat is fragile to noise.** **A
single mistaken defection triggers endless mutual retaliation.** **Generous tit-for-tat or
contrite strategies handle errors far better**, and in noisy environments they outperform.
**⚠️ And no strategy is universally best — success depends entirely on the population you
face**, which is §14 → `gametheory-evolutionary-empirical-limits-and-computation`'s point.

---
