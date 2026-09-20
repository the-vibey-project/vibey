---
name: endeavour-satellites-flight-software-and-instruments
description: "Use when designing or reviewing a satellite or space probe — picking an orbit regime and understanding the constraint that defines it, writing flight software whose hardware flips its own bits, building FDIR and a safe mode that survives a month, designing commands and telemetry to CCSDS, planning an in-flight software update, choosing science instruments against mass, power and data-volume budgets, or meeting planetary protection requirements. Part 7 of 12 of the Military Science, Rockets, Space, Fusion, and Mars reference."
---

# Satellites, Flight Software, Instruments, and Planetary Protection

> **Part 7 of 12** of the *Military Science, Rockets, Space, Fusion, and Mars* reference (plugin
> `military-space-rockets-and-fusion`), covering §26–§28 — bus and payload with the orbit regimes and
> the constraint that defines each, flight software from FDIR to in-flight update, scientific
> instrumentation, and planetary protection. Sibling skills:
> `endeavour-military-theory-levels-of-war-and-deterrence` (§1–§3 — what military science is, Clausewitz and the canon, the levels of war, deterrence and nuclear strategy),
> `endeavour-logistics-doctrine-modern-conflict-and-the-law` (§4–§6 — force structure and logistics, doctrine, intelligence and procurement, modern conflict, and the law of armed conflict),
> `endeavour-rocket-equation-nozzles-engines-and-propellants` (§7–§10 — Tsiolkovsky and staging, nozzle thermodynamics and the chamber, turbomachinery, engine cycles and cooling, propellants and density impulse),
> `endeavour-orbits-ascent-structures-and-reentry` (§11–§16 — vis-viva, manoeuvres and perturbations, the ascent Δv budget, aerodynamic loads and structures, guidance and control, reentry physics, failure physics),
> `endeavour-mission-architecture-and-spacecraft-subsystems` (§17–§22 — mission architecture, power and thermal, communications, navigation and autonomy, attitude control, in-space propulsion and EDL, human physiology, life support and ISRU, reliability and margins),
> `endeavour-fusion-physics-confinement-and-engineering` (§23–§25 — fusion physics and the Lawson criterion, magnetic and inertial confinement, why fusion is hard to engineer, and the nuclear background),
> `endeavour-the-martian-environment-and-in-situ-resources` (§29–§30 — Mars as engineering parameters, and Mars resources and ISRU),
> `endeavour-mars-mission-design-and-settlement` (§31–§32 — Mars mission design, and habitats, mobility, ECLSS closure and the psychological challenge),
> `endeavour-terraforming-warming-and-the-magnetic-field-problem` (§33–§35 — terraforming theory and the three thresholds, atmospheric thickening and warming, the magnetic field problem),
> `endeavour-ecopoiesis-oxygen-timelines-and-ethics` (§36–§38 — ecopoiesis and the oxygen problem, timelines and paraterraforming, ethics, governance and Venus),
> `endeavour-reference` (§39–§40 — the complete glossary and the complete further-reading list),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. The physics and the design principles here are durable; specific missions,
> standards revisions and flight-hardware practice do move.

A satellite or space probe is a **spacecraft bus** — the supporting infrastructure — plus a
**payload**, the instrument or communication package that justifies the mission. The bus provides
power, thermal control, attitude control, propulsion, communications, command and data handling, and
structure. The payload is what the mission is *for*. Everything else in this skill is what happens
when that payload has to survive, be commanded, and return its data.

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

## §27 Flight software: FDIR, command and telemetry, and in-flight update

Three properties make spacecraft software different from all other software.

1. **You cannot patch your way out.** Uplink is bandwidth-limited, latency-bound, and sometimes
   impossible. A bug that bricks the receiver ends the mission.
2. **The hardware is actively hostile.** Radiation flips bits in RAM and registers with no warning
   and no error signal. Software must assume its own memory is corrupting underneath it.
3. **Correct-but-late is wrong.** A control loop that misses its deadline has failed regardless of
   the answer it eventually produces.

> **DETERMINISM OUTRANKS THROUGHPUT.** That ordering inverts almost every instinct from server-side
> engineering, where throughput is the headline number and a late answer is merely slow. Here a late
> answer is a wrong answer, and a fast average with an unbounded tail is a failed design.

### FDIR: fault detection, isolation, and recovery

FDIR is **the organizing principle of flight software, not a feature of it**. The chain:

- **Detect** — limit checks, watchdogs, consistency checks, checksums, heartbeat monitors.
- **Isolate** — determine *which* component, avoiding misattribution. This is **the hardest step**:
  a detector fires on a symptom, and the symptom is rarely local to the fault.
- **Recover** — an escalation ladder: retry → reconfigure to a redundant unit → reset component →
  reset processor → safe mode. Redundancy types and common-cause failure are §22 →
  `endeavour-mission-architecture-and-spacecraft-subsystems`.

**Safe mode is the design that saves missions**: power-positive, thermally stable, Sun- or
Earth-pointed, minimal software, survivable indefinitely awaiting ground instruction. Every
deep-space mission enters safe mode. **The design question is not whether, but whether it can sit
there for a month without degrading.** The operational companions to safe mode — command loss timers
that reconfigure after N days without contact — are §19 →
`endeavour-mission-architecture-and-spacecraft-subsystems`.

### The hard-won lessons

- **Fault protection that misfires is itself a hazard.** A spurious safe-mode entry during orbit
  insertion or EDL can lose the mission, so critical sequences **inhibit selected fault responses**.
- **Don't recover into the fault.** Repeated automatic resets that re-trigger the same condition burn
  power and can exhaust a resource.
- **Log everything before acting.** The telemetry that explains a fault is often lost in the recovery
  that follows it.

### Command and telemetry

**CCSDS is the international standard set, and it is genuinely worth following rather than
inventing.** Command design principles:

- **Idempotent where possible** — a retransmitted command should not do the thing twice.
- **Two-stage arm/fire for hazardous commands** — deployments, pyros, engine starts.
- **Validate before execute** — checksum, authenticate, range-check every parameter.
- **Reject, don't clamp.** Silently clamping an out-of-range parameter hides the ground error that
  produced it, which is the error you actually needed to see.

Four telemetry types, each doing a different job:

| Type | What it is | Why it exists |
|---|---|---|
| Housekeeping | Periodic state | The continuous health picture |
| Event / EVR messages | The spacecraft's log | **Your only debugger** |
| Science data | The payload's output | The reason for the mission |
| Diagnostic dwell | Read arbitrary memory addresses | Indispensable for in-flight debugging |

**Design telemetry for the anomaly you haven't had yet.** The recurring operational regret is
insufficient telemetry to diagnose a fault after it occurs — and by then the channel list is fixed.

### In-flight software update

> **THE HIGHEST-STAKES OPERATION IN THE DISCIPLINE.** Six design rules, each written in blood:
> (1) the bootloader must be immutable, or dual-redundant with a golden image; (2) uplink to inactive
> memory, verify checksum, then switch; (3) automatic rollback on failure to check in after N
> minutes; (4) never patch the receive chain and the patch mechanism at once; (5) test the exact
> uplink product on the exact testbed configuration; (6) keep patch granularity small enough to fit
> the uplink budget. **A failed update that bricks the command receiver is unrecoverable and has
> ended missions.**

The counterexample worth knowing: **Voyager received a software patch in 2023–24 to work around
degraded memory, 46 years after launch**, on a system whose original engineers had retired or died.
That is only possible because the update path was designed conservatively from the start — the whole
case for rules that look paranoid on the ground.

---

## §28 Scientific instrumentation and planetary protection

**The measurement drives the mission.** Instrument selection is the first real decision in the design
cascade, and everything downstream — pointing, power, data volume, thermal — is sized from it
(§17 → `endeavour-mission-architecture-and-spacecraft-subsystems`).

### The instrument families

**Remote sensing:**

- **Imagers** — visible, IR, UV.
- **Spectrometers** — reflectance, emission, Raman, and **mass spectrometers, the workhorses doing
  most of the compositional science**.
- **Radar and sounders** — subsurface structure.
- **Lidar and altimeters.**
- **Magnetometers** — usually on a boom, because the spacecraft is magnetically dirty.
- **Particle and field instruments.**

**In situ:**

- **APXS.**
- **LIBS** — laser composition at standoff distance, **which transformed rover operations**, because
  it removes the need to drive to and contact every target before knowing what it is.
- **Gas chromatograph–mass spectrometers.**
- **Seismometers.**
- **Meteorology packages.**
- **Drills and sample handling.**

### The constraints that shape instrument design

Mass and power; **data volume, often the true limit on science return** rather than instrument
capability — the link budget behind that limit, and the Voyager and New Horizons numbers that show
it, are §19 → `endeavour-mission-architecture-and-spacecraft-subsystems`; thermal and cryogenic
needs; radiation tolerance; **calibration using onboard targets, because you cannot recalibrate
against a lab standard after launch**; contamination control; and pointing stability.

### Planetary protection

Legally grounded in the **Outer Space Treaty (1967), Article IX**, and implemented through **COSPAR
policy**.

| Category | Scope | What it imposes |
|---|---|---|
| I | No interest — Moon, Sun | — |
| II | Interest, remote contamination risk | Documentation only |
| III / IV | Mars, Europa, Enceladus | Bioburden limits, cleanroom assembly, and for some categories sterilization |
| V | Sample return | "Restricted Earth return" requires containment on the way back |

**Two directions, two different worries.** **Forward contamination** protects the science — finding
your own Earth microbes and calling it life would be the worst possible outcome — and arguably any
indigenous biosphere. **Backward contamination** is the sample-return problem.

The methods: **dry heat microbial reduction** — Viking baked its entire lander at **112 °C for 30
hours**, expensive and hard on hardware; **vapour hydrogen peroxide**; **cleanroom assembly**; and
**bioburden assay**.

> **CATEGORY IV CLOSES OFF PRECISELY WHERE THE ASTROBIOLOGY IS.** Compliance materially constrains
> design, adds cost, and restricts where you may land: **special regions — where liquid water might
> exist — are effectively off-limits to non-sterilized hardware.** The Martian conditions a special
> region turns on — the **580 Pa CO₂ partial pressure** against water's **611 Pa** triple point, and
> the **perchlorate brines** that can exist transiently anyway — are §29 →
> `endeavour-the-martian-environment-and-in-situ-resources`; the ethical
> question this framework exists to hold open — whether a biosphere may be extinguished to make a
> second Earth — is §38 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics`.
