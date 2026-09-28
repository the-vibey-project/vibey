---
id: skill-13-datasheets-and-selection-1877b5a1af
purpose: 13 datasheets and selection
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-test-selection-safety-and-debugging/SKILL.md
requires: ["skill-12-test-equipment-984b6f376a"]
links: ["skill-14-safety-41d60f128d"]
---

## §13. Datasheets and Selection

**⚠️ Read in this order**: absolute maximum ratings (⚠️ **these are *destruction* limits,
not operating conditions — a part operated at abs max is out of spec, not fine**) →
recommended operating conditions → electrical characteristics **with their test
conditions** → typical application circuit → package and thermal → **errata**.

**⚠️ The word "typical" is doing enormous work.** Design to **min/max**, not typical.
**Every spec has test conditions** — a `R_DS(on)` at `V_GS = 10 V` tells you nothing about
your 3.3 V drive (§5.3 → `ee-semiconductors-op-amps-logic-and-power`).

**Selection practicalities**: **derate** (voltage 50%+ on tantalums and electrolytics,
power 50%, current well below saturation), check **temperature range** (commercial /
industrial / automotive), **package** vs your assembly capability, ⚠️ **lifecycle status —
"NRND" or "obsolete" is a design-in you'll regret**, and **second sources**.

**⚠️ Availability is a design constraint.** Check stock at distributors before committing.
A perfect design with a 52-week lead-time part is not a design.

---
