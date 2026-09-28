---
id: skill-15-reentry-physics-c14a072dcf
purpose: 15 reentry physics
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-orbits-ascent-structures-and-reentry/SKILL.md
requires: ["skill-14-guidance-and-control-c3e724f2f2"]
links: ["skill-16-failure-physics-and-normalization-of-deviance-19616a3876"]
---

## §15 Reentry physics

> **REENTRY HEATING IS COMPRESSION, NOT FRICTION.** The **bow shock compresses and heats the air**, and
> the vehicle is heated by that gas. A **blunt body pushes a detached bow shock ahead of itself,
> dumping most of the energy into the air rather than into the vehicle**. A slender, "aerodynamic"
> shape produces an **attached** shock and concentrates heating on the surface — it would be destroyed.
> This is why **every reentry vehicle from Mercury to Orion to Dragon is bluff**.

Stated as energy, the problem is to **dispose of ~30 MJ/kg (LEO) or ~60 MJ/kg (lunar return) without
depositing it in the vehicle**.

**Peak deceleration depends only on entry velocity and flight path angle — not on mass or drag area:**

    a_max = v_e² · sin γ / (2·e·H)

Apollo: **~6.5 g**. A ballistic Soyuz abort: **~9 g**.

**Stagnation-point heating — the Sutton-Graves relation:**

    q_s = k · √(ρ/R_n) · v³

Two consequences follow directly from the exponents:

| Scaling | Consequence |
|---|---|
| **q ∝ v³** | lunar return at **11 km/s** versus LEO at **7.8 km/s** is **2.8× the heat flux** |
| **q ∝ 1/√R_n** | **a blunter nose reduces peak heating** — another argument for bluff bodies |

**Total heat load scales differently from peak flux.** A **shallow entry lowers peak flux but raises
total load**. The design rule that falls out: **peak flux sizes the material; total load sizes the
thickness.**

**The entry corridor** is bounded on both sides — **too steep exceeds heating and g-limits; too shallow skips
out**. For **Apollo lunar return the corridor was about ±1° in flight path angle** — a genuinely tight target
from **400,000 km away**. The Martian version of this squeeze, where the atmosphere is too thick to ignore and
too thin to stop you, is §20 → `endeavour-mission-architecture-and-spacecraft-subsystems` and
§31 → `endeavour-mars-mission-design-and-settlement`.
