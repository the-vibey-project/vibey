---
id: skill-13-matching-markets-622179f1f9
purpose: 13 matching markets
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-bargaining-cooperative-mechanism-design-and-matching/SKILL.md
requires: ["skill-12-mechanism-design-and-auctions-0de48cdb19"]
links: []
---

## §13. Matching Markets

**⚠️ Markets without prices — where money can't or shouldn't clear the market.**

**Gale-Shapley deferred acceptance (1962)** — ⚠️ **always produces a stable matching, in
polynomial time.**
**Properties worth knowing precisely:**
- ⚠️ **The side that *proposes* gets their best achievable stable match; the receiving side
  gets their worst.** **Which side proposes is a distributional choice, not a technical
  detail.**
- **Truth-telling is dominant for the proposing side; the receiving side can
  manipulate.**
- ⚠️ **Stability — no pair who'd both rather be with each other — is the property that
  makes matching markets survive.** **Roth's empirical work showed that unstable
  clearinghouses historically unravelled and stable ones persisted.**

**Applications**: **medical residency matching (NRMP)**, **school choice** (⚠️ **and the
Boston mechanism's replacement by deferred acceptance is a real policy win from theory**),
**kidney exchange** (⚠️ **cycles and chains in a directed graph — Roth, Sönmez, Ünver, and
it has saved thousands of lives**).
**⚠️ Top trading cycles** for allocation with existing endowments.
