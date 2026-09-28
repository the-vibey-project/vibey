---
id: skill-8-ascent-trajectory-e0899e4ffb
purpose: 8 ascent trajectory
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-orbital-mechanics-and-ascent/SKILL.md
requires: ["skill-7-orbital-mechanics-3109771761"]
links: []
---

## §8. Ascent Trajectory

**[DURABLE] The Δv budget in full:**
```
Δv_required = Δv_orbital + Δv_gravity + Δv_drag + Δv_steering − Δv_rotation
```

**Gravity loss**: `∫ g·sin γ dt` where γ is flight path angle.
⚠️ **This is the big one — 1.2–1.7 km/s for a typical launch.** Minimized by pitching over
early and by high initial thrust-to-weight. **At T/W = 1.0 you hover and lose 9.8 m/s per
second of hovering**; practical liftoff T/W is **1.2–1.4**, and higher isn't automatically
better because it raises max-Q and structural loads (§9 → `rocket-aerodynamics-structures-guidance-and-reentry`).

**Drag loss**: `∫ (D/m) dt` — typically **only 100–150 m/s**, ⚠️ **much smaller than people
expect**, because the vehicle is through the dense atmosphere quickly. This is why
aerodynamic optimization matters far less for rockets than for aircraft.

**Steering loss**: `∫ a·(1 − cos α) dt` — thrust not aligned with velocity.

**Earth rotation credit**: `465·cos(latitude)` m/s eastward.
Kourou (5.2°N): 463 m/s. Cape Canaveral (28.5°N): 409 m/s. Baikonur (45.6°N): 325 m/s.
⚠️ **Which is why equatorial sites are valuable and why polar/retrograde launches forfeit
this entirely** (and pay double to cancel it).

**The gravity turn**: after a vertical rise, pitch slightly, then let gravity rotate the
velocity vector with **zero angle of attack**. ⚠️ **Zero-α is not an efficiency choice —
it's a structural one.** Aerodynamic side loads on a long thin cylinder at angle of attack
generate bending moments that the structure can't take (§9 → `rocket-aerodynamics-structures-guidance-and-reentry`, §10 → `rocket-aerodynamics-structures-guidance-and-reentry`).

**Max-Q** occurs where `q = ½ρv²` peaks — ⚠️ **typically 30–90 s, at 10–15 km, at
20–40 kPa.** Density is falling while velocity rises; the product peaks. **Engines throttle
down through it** to limit loads.
