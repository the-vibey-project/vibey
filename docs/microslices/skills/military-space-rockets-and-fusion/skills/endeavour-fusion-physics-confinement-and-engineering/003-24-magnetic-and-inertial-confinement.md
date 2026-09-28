---
id: skill-24-magnetic-and-inertial-confinement-2657877a5e
purpose: 24 magnetic and inertial confinement
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-fusion-physics-confinement-and-engineering/SKILL.md
requires: ["skill-23-fusion-physics-the-candidate-reactions-and-the-lawson-criterion-57f66b235a"]
links: ["skill-25-why-fusion-is-hard-to-engineer-and-the-nuclear-background-8b7dbe5f6e"]
---

## §24 Magnetic and inertial confinement

### Magnetic confinement

Charged particles spiral along field lines, and a toroidal geometry closes those lines so they never
leave. **A purely toroidal field does not confine.** Field curvature and gradient cause
charge-dependent drift, the plasma separates, and it is lost. You need a twist — a **poloidal
component** — and the two leading configurations are two opposite answers to where that twist comes
from.

| Configuration | Source of the poloidal twist | Strength | Weakness |
|---|---|---|---|
| **Tokamak** | A current driven in the plasma itself | Axisymmetric and best-understood | That current is a free energy source for disruptions |
| **Stellarator** | External coils only | Intrinsically steady-state and disruption-free | Coil geometry is fiendishly complex, and only became tractable with modern computation |

Others in the family: **spherical tokamak, reversed field pinch, mirrors, FRC**.

**The problem set:**

- **Disruptions** — a sudden loss of confinement dumping enormous energy onto the wall. **The main
  risk in tokamaks**, and the direct consequence of storing energy in a plasma current.
- **MHD instabilities**.
- **ELMs** (edge-localized modes).
- **Turbulent transport** — this is what **sets τ_E**, and it is why **empirical scaling laws still
  substitute for first-principles prediction**. You cannot yet compute confinement time from first
  principles for a machine that has not been built.
- **Divertor heat load** — where the exhaust power lands; the number is under §25 below.

### Inertial confinement

Compress and heat a fuel capsule so fast that **inertia** confines it long enough to burn — over
nanoseconds. No field holds the fuel; its own mass does, briefly.

- **Direct drive** — lasers on the capsule.
- **Indirect drive** — lasers heat a high-Z **hohlraum** which re-radiates X-rays. More uniform, less
  efficient. **This is NIF's approach.**

**The physics obstacles**, in order of how much they dominate:

1. **Rayleigh-Taylor instability during compression — the dominant one.** Any surface imperfection
   grows catastrophically as the implosion proceeds.
2. Required implosion **symmetry**.
3. **Laser-plasma instabilities**.
4. **Capsule fabrication tolerances** — the target is a precision-manufactured object, and it is
   consumed in nanoseconds.

**Repetition rate is the gulf between ignition and a power plant.** NIF fires occasionally; a plant
would need **several shots per second, with a fresh target each time**. Ignition demonstrates the
physics of the burn; nothing about it demonstrates a machine that can do it continuously, cheaply,
and with targets manufactured at that rate.
