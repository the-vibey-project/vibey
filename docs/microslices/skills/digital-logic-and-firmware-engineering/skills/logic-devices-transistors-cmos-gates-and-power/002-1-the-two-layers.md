---
id: skill-1-the-two-layers-44e3cd10bb
purpose: 1 the two layers
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-0-routing-dcea3e799a"]
links: ["skill-2-diodes-4df2d0fa93"]
---

## §1. The Two Layers

```
⚠️ WHERE THIS FILE SITS
   device physics ────────── a semiconductor reference
   ⚠️ TRANSISTORS AS SWITCHES ──── §2-§4     ← here
   ⚠️ CMOS GATES ───────────────── §5-§9     ← here
   ⚠️ BOOLEAN LOGIC ────────────── §10-§13   ← here
   ⚠️ SEQUENTIAL AND TIMING ────── §14-§19   ← here
   microarchitecture ─────── a microarchitecture reference
   ⚠️ FIRMWARE AND BOOT ────────── §20-§25   ← here
   OS and applications ───── elsewhere
⚠️ THE SYMMETRY WORTH NOTICING  ⚠️ both layers are ones people
   treat as solved and invisible — and both are where the
   hardest-to-diagnose failures live. ⚠️ A setup-time violation
   and a firmware bug share a signature: intermittent,
   environment-dependent, and invisible at the layer above
```

---

# PART I — DEVICES AS SWITCHES
