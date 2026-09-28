---
id: skill-12-instrumentation-806bb6e354
purpose: 12 instrumentation
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-human-factors-life-support-and-reliability/SKILL.md
requires: ["skill-11-radiation-environments-and-shielding-36c93afb91"]
links: ["skill-13-planetary-protection-09eb27d8a3"]
---

## §12. Instrumentation

**[DURABLE] The measurement drives the mission** (§1.1 → `space-mission-architecture-and-trajectory`). The families:

**Remote sensing** — imagers (visible, IR, UV), **spectrometers** (⚠️ **the workhorses:
reflectance, emission, Raman, and mass spectrometers do most of the compositional
science**), radar and sounders (⚠️ **subsurface structure — MARSIS and SHARAD map Martian
ice**), lidar/altimeters, magnetometers (⚠️ **usually on a boom, because the spacecraft is
magnetically dirty**), and particle and field instruments.

**In situ** — APXS, LIBS (⚠️ **ChemCam's laser gets composition at standoff distance, which
transformed rover operations**), gas chromatograph–mass spectrometers, seismometers
(⚠️ **InSight's SEIS measured Mars's interior structure for the first time**),
meteorology packages, and drills and sample handling.

**⚠️ The constraints that shape instrument design**: mass and power, **data volume**
(§5.2 → `space-power-thermal-comms-and-navigation` — ⚠️ **often the true limit on science return**), **thermal and cryogenic needs**,
**radiation tolerance**, **calibration** (⚠️ **onboard targets, because you cannot
recalibrate against a lab standard after launch**), **contamination control** (§13), and
**pointing stability**.

---
