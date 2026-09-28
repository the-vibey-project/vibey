---
id: skill-26-satellite-and-space-probe-design-types-and-orbits-bf7b914aba
purpose: 26 satellite and space probe design types and orbits
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-satellites-flight-software-and-instruments/SKILL.md
requires: []
links: ["skill-27-flight-software-fdir-command-and-telemetry-and-in-flight-update-559741efc0"]
---

## §26 Satellite and space probe design, types, and orbits

> **EVERYTHING IN THE DESIGN REDUCES TO MASS.** Power converts to mass, data rate converts to mass,
> reliability converts to mass — and propellant mass is *exponential* in Δv. That last clause is why
> the conversion is not a fair trade: an extra kilogram of payload is paid for at the mass ratio of
> every burn that follows it. The exponent is Tsiolkovsky's (§7 →
> `endeavour-rocket-equation-nozzles-engines-and-propellants`); the design cascade that this
> bookkeeping drives is §17 → `endeavour-mission-architecture-and-spacecraft-subsystems`.

The bus subsystems themselves — power, thermal, communications, navigation, attitude control and
in-space propulsion — are covered in §18–§20 →
`endeavour-mission-architecture-and-spacecraft-subsystems`. What follows is the orbit side: where a
spacecraft is put, and the one constraint that governs each regime.

### Satellite types and orbits

| Type | Orbit | Primary Use | Key Constraint |
|---|---|---|---|
| LEO communications | 400–1,200 km | Starlink, Iridium, Earth observation | Drag, constellation management |
| Sun-synchronous | 600–900 km, ~98° | Imaging, weather, reconnaissance | Consistent lighting via J₂ precession |
| GEO communications | 35,786 km, 0° | TV, data relay, weather | Station-keeping ~50 m/s/yr, latency |
| Molniya | Highly elliptical, 63.4° | High-latitude communications | Apsidal precession frozen by inclination |
| Navigation | MEO ~20,000 km | GPS, Galileo, GLONASS | Constellation geometry, atomic clock stability |
| Scientific (deep space) | Interplanetary | Planetary probes, observatories | Power (solar 1/r²), light-time, autonomy |

**Reading the table — each row is a different binding constraint, not a different altitude.**

- **LEO communications, 400–1,200 km.** Drag is the governing physical effect and constellation
  management the governing operational one — the first sets how long a satellite lasts and how
  uncertain its reentry date is, the second is the standing problem of keeping many satellites
  phased, separated and replaced. Drag's altitude and solar-activity dependence is §11 →
  `endeavour-orbits-ascent-structures-and-reentry`.
- **Sun-synchronous, 600–900 km at ~98°.** The retrograde inclination is chosen so that J₂ nodal
  regression matches Earth's mean motion about the Sun, holding local solar time constant so every
  image of a site is taken under the same lighting. It is a perturbation exploited rather than
  fought; the geometry is §11 → `endeavour-orbits-ascent-structures-and-reentry`.
- **GEO communications, 35,786 km at 0°.** Two constraints, both permanent: **station-keeping at
  ~50 m/s/yr**, which sets the propellant the spacecraft must carry for its whole service life
  (§20 → `endeavour-mission-architecture-and-spacecraft-subsystems`), and **latency**, which is
  simply the distance and does not improve.
- **Molniya, highly elliptical at 63.4°.** The inclination is not a coverage choice — it is the
  value that **freezes apsidal precession**, so apogee stays where it was put and the long slow
  apogee pass keeps recurring over the same high-latitude region: §11 →
  `endeavour-orbits-ascent-structures-and-reentry`.
- **Navigation, MEO ~20,000 km.** Constrained by **constellation geometry** — a user's position fix
  is only as good as the spread of satellites in view — and by **atomic clock stability**, because
  the measurement being made is time.
- **Scientific, interplanetary.** Three constraints at once: **power**, because solar flux falls as
  1/r² (§18 → `endeavour-mission-architecture-and-spacecraft-subsystems`); **light-time**, which
  makes teleoperation impossible beyond the Moon; and **autonomy**, which is forced by that
  light-time rather than chosen (§19 →
  `endeavour-mission-architecture-and-spacecraft-subsystems`). Autonomy is where this skill picks up
  the thread: it has to be implemented in software, on a computer that is being irradiated.

---
