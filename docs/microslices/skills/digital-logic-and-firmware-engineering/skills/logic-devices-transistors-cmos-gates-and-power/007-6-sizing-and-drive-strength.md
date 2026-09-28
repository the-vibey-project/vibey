---
id: skill-6-sizing-and-drive-strength-36127acc66
purpose: 6 sizing and drive strength
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-5-static-cmos-gates-adb0daf92c"]
links: ["skill-7-other-logic-families-2091a99b66"]
---

## §6. Sizing and Drive Strength

**⚠️ Why pMOS is usually wider**: ⚠️ **hole mobility is roughly 2–3× lower than electron
mobility, so a pMOS must be proportionally wider to match an nMOS's drive.** ⚠️ **A
"balanced" inverter uses that ratio; ⚠️ deliberately unbalanced sizing skews the switching
threshold, which is sometimes what you want.**
**⚠️ Series stacks need upsizing** — ⚠️ **two devices in series each need roughly double
width to match a single device's drive.**
**⚠️ LOGICAL EFFORT** is the design method worth knowing: ⚠️ **it separates a gate's
intrinsic difficulty from its load, giving a systematic way to size a path and to find the
optimal number of stages — and the well-known result is that a fanout of roughly 4 per
stage is near-optimal.**
**⚠️ Buffer insertion and repeaters** — ⚠️ **driving a large load or a long wire directly is
slow; a chain of progressively larger buffers is faster despite adding stages.**
**⚠️ Drive strength in a cell library** (§9 → `logic-standard-cells-boolean-minimization-and-arithmetic`) is exactly this made discrete: ⚠️ **X1, X2, X4
versions of the same logic function.**

---
