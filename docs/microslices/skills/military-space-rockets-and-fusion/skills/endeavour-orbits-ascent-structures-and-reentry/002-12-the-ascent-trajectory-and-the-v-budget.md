---
id: skill-12-the-ascent-trajectory-and-the-v-budget-eadd2b2c32
purpose: 12 the ascent trajectory and the v budget
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-orbits-ascent-structures-and-reentry/SKILL.md
requires: ["skill-11-orbital-mechanics-vis-viva-manoeuvres-and-perturbations-325f2023fb"]
links: ["skill-13-aerodynamic-loads-and-thin-walled-structures-06799f35c8"]
---

## §12 The ascent trajectory and the Δv budget

The full budget is additive, with one term working in your favour:

    Δv_required = Δv_orbital + Δv_gravity + Δv_drag + Δv_steering − Δv_rotation

| Term | Sign | Magnitude | What sets it |
|---|---|---|---|
| Δv_orbital | + | the orbit you want | vis-viva (§11 above) |
| **Δv_gravity** | + | **1.2–1.7 km/s** for a typical launch | time spent fighting gravity — minimized by pitching over early and by high initial thrust-to-weight |
| Δv_drag | + | **only 100–150 m/s** | much smaller than people expect, because the vehicle is through the dense atmosphere quickly |
| Δv_steering | + | *(no magnitude given in this reference)* | departures from the ideal thrust direction |
| **Δv_rotation** | **−** | **465·cos(latitude) m/s** eastward — Cape Canaveral gets **409 m/s** | launch-site latitude; polar and retrograde launches forfeit it |

**Gravity loss is the big one**, and practical liftoff **thrust-to-weight is 1.2–1.4**. The Earth rotation
credit is why **equatorial sites are valuable**.

### The gravity turn — and why zero-α is structural

After a vertical rise the vehicle pitches slightly, then lets gravity rotate the velocity vector at
**zero angle of attack**.

> **ZERO-α IS NOT AN EFFICIENCY CHOICE — IT IS A STRUCTURAL ONE.** Aerodynamic side loads on a long
> thin cylinder at angle of attack generate bending moments the structure cannot take. The trajectory
> is shaped by what the airframe survives, not by what the propulsion prefers.

**Max-Q** occurs where **q = ½ρv²** peaks — **typically 30–90 seconds, at 10–15 km altitude, at
20–40 kPa**. Engines throttle down through it to limit loads.
