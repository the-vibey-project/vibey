---
id: skill-6-machine-elements-a3309a4363
purpose: 6 machine elements
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-machine-elements-mechanisms-and-tolerances/SKILL.md
requires: []
links: ["skill-7-mechanisms-and-kinematics-f0bafc02d5"]
---

## §6. Machine Elements

**⚠️ Most mechanical design is SELECTING standard components, not designing new ones.**
```
⚠️ FASTENERS  ⚠️ a bolted joint works by CLAMPING — preload creates
   friction that carries the load, and the bolt should ideally not
   see shear directly. ⚠️ This is why TORQUE SPEC matters and why
   under-torqued bolts fatigue and fail
   ⚠️ Torque is a poor proxy for preload (friction scatter is large),
   which is why critical joints use angle or stretch measurement
⚠️ BEARINGS  rolling vs plain vs fluid film. ⚠️ Rated by L10 life —
   a STATISTICAL life at which 10% have failed, not a guarantee
⚠️ GEARS  ratio, module/pitch, ⚠️ backlash (lost motion on reversal —
   a real problem in positioning systems)
SPRINGS · SEALS (⚠️ dynamic seals are a common failure point) ·
COUPLINGS · belts and chains
```
**⚠️ Standard parts exist and should be used**: ⚠️ **ISO/ANSI threads, standard bearing
sizes, stock material thicknesses.** **⚠️ A custom fastener is a supply chain liability
forever** (§22 → `mfg-dfm-metrology-plm-npi-and-what-transfers`).
**⚠️ Threadlocking, prevailing-torque nuts and lock washers** — ⚠️ **and note that ordinary
split lock washers have been shown to be largely ineffective, which is folklore that
persists.**

---
