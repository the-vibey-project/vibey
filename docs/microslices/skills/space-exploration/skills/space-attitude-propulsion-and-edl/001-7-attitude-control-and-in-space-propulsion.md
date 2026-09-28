---
id: skill-7-attitude-control-and-in-space-propulsion-f21a28680f
purpose: 7 attitude control and in space propulsion
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-attitude-propulsion-and-edl/SKILL.md
requires: []
links: ["skill-8-edl-and-surface-operations-f75329a97a"]
---

## §7. Attitude Control and In-Space Propulsion

**Attitude sensing**: star trackers (best, arcsecond-class), sun sensors, horizon sensors,
magnetometers (LEO only), gyros.

**Actuation**: **reaction wheels** (⚠️ **precise, but they saturate and must be
desaturated — and wheel failure has crippled missions; Kepler and Hayabusa both lost
wheels**), **control moment gyros** (higher torque, used on ISS), **thrusters** (fast,
consume propellant), **magnetorquers** (LEO only), **spin stabilization** (⚠️ **simple and
robust, at the cost of pointing flexibility**), **gravity-gradient**, and
⚠️ **solar radiation pressure**, which Kepler used as a virtual third wheel after two
failed — a genuinely elegant recovery.

**In-space propulsion:**

| Type | Isp (s) | Use |
|---|---|---|
| **Cold gas** | 50–70 | Simple, small ΔV, contamination-free |
| **Monopropellant (hydrazine)** | 220–235 | ⚠️ **The RCS workhorse** |
| **Bipropellant (MMH/NTO)** | 300–330 | Orbit insertion, hypergolic and storable |
| **Solid** | 280–300 | Single-burn kick stages |
| **Hall thruster** | 1,500–2,500 | ⚠️ **Station-keeping and orbit raising, now standard** |
| **Gridded ion** | 3,000–4,000 | ⚠️ **Dawn visited two main-belt bodies — impossible chemically** |
| **Solar sail** | ∞ | No propellant; tiny thrust |

**⚠️ The electric propulsion trade, stated properly**: 10× the Isp means ~1/10 the
propellant for the same Δv, **but thrust is millinewtons, so burns last months and the
power system must be sized to feed it** — the mass moves from the propellant tank to the
solar arrays. **It wins when the mission has time and the Δv is large.**

**Station-keeping**: **GEO needs ~50 m/s/yr** (north-south dominates, against lunisolar
perturbations); **LEO drag makeup**; **halo orbits need small but continual maintenance**
because they're unstable.

---
