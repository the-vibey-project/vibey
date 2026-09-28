---
id: skill-11-orbital-mechanics-vis-viva-manoeuvres-and-perturbations-325f2023fb
purpose: 11 orbital mechanics vis viva manoeuvres and perturbations
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-orbits-ascent-structures-and-reentry/SKILL.md
requires: []
links: ["skill-12-the-ascent-trajectory-and-the-v-budget-eadd2b2c32"]
---

## §11 Orbital mechanics: vis-viva, manoeuvres, and perturbations

From Newton, the two-body problem gives **conic-section orbits**. The **vis-viva equation** is the
single most useful formula in mission design:

    v² = μ · (2/r − 1/a)

> **ENERGY DEPENDS ONLY ON THE SEMI-MAJOR AXIS.** Everything else about the orbit — eccentricity,
> orientation, where you happen to be in it — drops out of the energy budget. Two numbers, r and a,
> and vis-viva gives you the speed.

The three relations that follow:

| Quantity | Relation | Note |
|---|---|---|
| Circular velocity | v = √(μ/r) | the speed that holds a given radius |
| Escape velocity | v = √(2μ/r) = **√2 · v_circ** | only **41% more** than circular |
| Period | T = 2π√(a³/μ) | Kepler's third |

Escape being only 41% above circular is the reason **interplanetary departure is cheaper than intuition
suggests** — you are not doubling the job you already did to reach orbit.

### Manoeuvres

The **Hohmann transfer** is two burns and the minimum-energy path between coplanar circular orbits.
Worked example, LEO (6,678 km) to GEO (42,164 km):

| Burn | What it does | Δv |
|---|---|---|
| Δv₁ | circular at 6,678 km → transfer ellipse | **2.513 km/s** |
| Δv₂ | transfer ellipse → circular at 42,164 km | **1.453 km/s** |
| **Coplanar total** | — | **3.966 km/s** |
| Inclination change of 28.5° at GEO | if the launch site forced one | **~1.8 km/s** |

**Bi-elliptic beats Hohmann when r₂/r₁ > 11.94** — counterintuitive, and genuinely used for some
high-energy transfers.

**Plane change:** Δv = 2v·sin(Δi/2). At LEO velocity a **28.5° plane change costs 3.8 km/s — more than
reaching GEO at all**.

> **LAUNCH-SITE LATITUDE IS A HARD MISSION CONSTRAINT, NOT A PREFERENCE.** Because plane change scales
> with the velocity you are already carrying, you launch directly into your target inclination rather
> than fixing it later, and when a plane change is unavoidable you do it at apoapsis where v is
> smallest. The same geometry decides which orbit regimes a given site can serve at all
> (§26 → `endeavour-satellites-flight-software-and-instruments`).

**The Oberth effect:** for a burn Δv at speed v, the energy change is

    Δε = v·Δv + Δv²/2

The **v·Δv** term means the same propellant buys more energy when you are moving faster — hence
departure burns at periapsis, and the value of **dropping deep into a gravity well before burning**.

### Perturbations

**J₂ (Earth oblateness) is the dominant perturbation**, and it has two elegant exploitations:

- **Sun-synchronous orbit** — choose the inclination so that nodal regression matches Earth's mean
  motion about the Sun. At 800 km that is **i ≈ 98.6°, retrograde**, and it keeps local solar time
  constant, which is why imaging satellites use it.
- **Molniya orbit** — set **5cos²i − 1 = 0**, i.e. **i = 63.4°**, which freezes apsidal precession so
  apogee stays over the northern hemisphere.

**Drag dominates below ~600 km**, and atmospheric density varies by **more than an order of magnitude with
solar activity** — which is why **reentry prediction is genuinely uncertain**, not merely imprecise.
