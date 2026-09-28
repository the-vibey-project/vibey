---
id: skill-14-injection-moulding-f1de7646f9
purpose: 14 injection moulding
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-process-families-machining-additive-and-moulding/SKILL.md
requires: ["skill-13-additive-manufacturing-36a35baf34"]
links: ["skill-15-sheet-metal-b3605ceb2a"]
---

## §14. Injection Moulding

**⚠️ The dominant process for plastic parts at volume, and its design rules are strict:**
```
⚠️ UNIFORM WALL THICKNESS — ⚠️ thick sections cool slowly and SINK,
   leaving visible depressions. Core out thick areas
⚠️ DRAFT ANGLE on every vertical face, or the part won't eject
⚠️ RIBS for stiffness instead of thick walls (⚠️ rib thickness
   typically ~50-60% of the wall to avoid sink marks)
⚠️ AVOID UNDERCUTS — they require side actions or lifters, which
   multiply tool cost
⚠️ GATE and PARTING LINE locations are visible; ⚠️ WELD LINES form
   where flow fronts meet and are structurally weak
⚠️ TOOLING IS THE CAPITAL COST — often five to six figures and
   weeks to months of lead time. ⚠️ A tool change is not a
   software patch
```
**⚠️ The economics**: ⚠️ **high tooling, very low unit cost, so the crossover versus
machining or AM is entirely about volume** (§19 → `mfg-dfm-metrology-plm-npi-and-what-transfers`).

---
