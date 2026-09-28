---
id: skill-24-positioning-and-sensing-12ef0f723b
purpose: 24 positioning and sensing
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-security-coexistence-and-positioning/SKILL.md
requires: ["skill-23-coexistence-0935160e1d"]
links: []
---

## §24. Positioning and Sensing

**⚠️ The techniques, in ascending order of accuracy and cost**:
⚠️ **RSSI trilateration (⚠️ crude — signal strength is a terrible distance proxy because
of multipath and obstruction, and this is why "proximity" beacons are so unreliable);
⚠️ FINGERPRINTING against a survey map; ⚠️ AoA/AoD requiring antenna arrays;
⚠️ TIME OF FLIGHT and TDoA, which is what UWB does well (§14 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`) and now Bluetooth Channel
Sounding (§25.2 → `wireless-reference`); ⚠️ and GNSS outdoors, with RTK for centimetre accuracy.**
**⚠️ RF SENSING** is a rapidly growing use: ⚠️ **detecting presence, motion, breathing and
gestures from CHANNEL STATE INFORMATION perturbations — ⚠️ and Wi-Fi Sensing (802.11bf)
standardizes it.**
> **⚠️ GOTCHA — RF sensing is a privacy problem, not just a feature.** ⚠️ **A network that
> can detect breathing through walls is doing surveillance regardless of intent, and this
> is an area where the capability is arriving well ahead of the norms.**
