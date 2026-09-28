---
id: skill-20-attitude-control-in-space-propulsion-and-entry-descent-and-landing-39aad0ce65
purpose: 20 attitude control in space propulsion and entry descent and landing
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mission-architecture-and-spacecraft-subsystems/SKILL.md
requires: ["skill-19-communications-navigation-and-autonomy-bf7f34e526"]
links: ["skill-21-human-physiology-life-support-and-isru-4840544458"]
---

## §20 Attitude control, in-space propulsion, and entry, descent and landing

**Sensing:** star trackers (arcsecond-class, best), sun sensors, horizon sensors, magnetometers (LEO
only), gyros.

**Actuation:** reaction wheels (precise, but they **saturate and must be desaturated**, and wheel
failure has crippled missions — **Kepler and Hayabusa both lost wheels**), control moment gyros
(higher torque, used on ISS), thrusters (fast, consume propellant), magnetorquers (LEO only), spin
stabilization (simple and robust, at the cost of pointing flexibility).

| Type | Isp (s) | Use |
|---|---|---|
| Cold gas | 50–70 | Simple, small ΔV, contamination-free |
| Monopropellant (hydrazine) | 220–235 | The RCS workhorse |
| Bipropellant (MMH/NTO) | 300–330 | Orbit insertion, hypergolic and storable |
| Hall thruster | 1,500–2,500 | Station-keeping and orbit raising, now standard |
| Gridded ion | 3,000–4,000 | Dawn visited two main-belt bodies — impossible chemically |
| Solar sail | ∞ | No propellant; tiny thrust |

**The electric propulsion trade, stated properly.** 10× the Isp means ~1/10 the propellant for the
same Δv — but thrust is millinewtons, so burns last months and the power system must be sized to
feed it. **The mass moves from the propellant tank to the solar arrays.** It wins when the mission
has time and the Δv is large. (Isp, the mass ratio and why propellant mass is exponential in Δv are
at §7 → `endeavour-rocket-equation-nozzles-engines-and-propellants`.)

**Station-keeping budgets.** GEO needs ~50 m/s/yr, with north-south dominant. LEO needs drag makeup.
Halo orbits need small but continual maintenance because they are unstable.

### EDL — the Martian squeeze

Mars EDL is the canonical hard case, and the reason is a genuine physical squeeze: **the atmosphere
is ~1% of Earth's — thick enough to demand a heat shield, too thin to slow you to safe landing speed
with parachutes alone.** The sequence, roughly seven minutes:

    entry interface (~125 km, ~5.5–7.5 km/s) → peak heating (~100 s), peak deceleration (~8–15 g)
      → supersonic parachute deploy (Mach 1.5–2.2, ~10 km) → heat shield jettison
      → radar/TRN acquisition → backshell separation → powered descent → touchdown

Everything is autonomous. The heating physics behind the blunt aeroshell — compression rather than
friction, the v³ scaling of stagnation-point flux, and the entry corridor — is at §15 →
`endeavour-orbits-ascent-structures-and-reentry`.

**Landing methods and their regimes:**

- **Airbags** (Pathfinder, MER) — mass-efficient, but cap landed mass around a few hundred kg.
- **Legs** (Viking, Phoenix, InSight) — the engine plume excavates regolith and can contaminate
  samples.
- **Sky crane** (MSL, Perseverance) — the correct answer for ~1-tonne rovers: it keeps the engines
  away from the surface and puts the wheels down directly.

**The landed-mass ceiling.** Mars EDL has historically capped landed mass near ~1 tonne, because
parachute area scales badly and supersonic retropropulsion was unproven. Scaling past it requires
either much larger decelerators or supersonic retropropulsion.
