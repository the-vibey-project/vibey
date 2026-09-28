---
id: skill-23-reliability-ddf00744e0
purpose: 23 reliability
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-pcb-assembly-reliability-design-flow-and-economics/SKILL.md
requires: ["skill-22-assembly-and-soldering-3f84242c57"]
links: ["skill-24-design-flow-f1f08e3935"]
---

## §23. Reliability

```
⚠️ THE BATHTUB CURVE  ⚠️ infant mortality (screened by burn-in,
   §19) → low constant random failure → ⚠️ WEAR-OUT
⚠️ THE INTRINSIC WEAR-OUT MECHANISMS
   ⚠️ ELECTROMIGRATION  metal atoms moved by current (§7)
   ⚠️ TDDB  time-dependent dielectric breakdown — the gate oxide
      fails after cumulative stress
   ⚠️ NBTI/PBTI  threshold voltage drifts over operating life
   ⚠️ HOT CARRIER INJECTION  energetic carriers damage the oxide
   ⚠️ These are why chips have a rated LIFETIME at a rated
   temperature and voltage — ⚠️ and why overclocking and running
   hot genuinely shorten it
⚠️ PACKAGE and BOARD  ⚠️ solder fatigue from CTE mismatch under
   thermal cycling (⚠️ the dominant board-level failure) ·
   delamination · popcorning of moisture-absorbed packages during
   reflow (hence moisture sensitivity levels and baking)
⚠️ ESD and latch-up  ⚠️ on-chip protection structures exist for this
⚠️ SOFT ERRORS  ⚠️ alpha particles and cosmic-ray neutrons flip
   memory bits. ⚠️ Not a defect — a physical inevitability, which
   is why ECC exists and why it matters at scale
⚠️ ARRHENIUS  ⚠️ reaction rates roughly double per 10 °C. Thermal
   management IS reliability engineering
```

---
