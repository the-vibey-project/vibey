---
name: endeavour-mission-architecture-and-spacecraft-subsystems
description: "Use when sizing or trading a spacecraft mission — picking flyby versus orbiter versus lander, solar versus radioisotope power, chemical versus electric propulsion, direct versus gravity assist, relay versus direct-to-Earth — or when you need the numbers behind a bus subsystem: solar flux at Mars or Jupiter, RTG output and efficiency, radiator area at a given temperature, a deep space link budget and light-time, reaction wheel saturation, Isp by thruster type, the Mars EDL sequence and its landed-mass ceiling, crew radiation dose and SANS, ECLSS closure ratios, MOXIE's demonstrated output, or the standard mass and Δv margin schedule and the failures that produced it. Part 5 of 12 of the Military Science, Rockets, Space, Fusion, and Mars reference."
---

# Space Mission Architecture and Spacecraft Subsystems

> **Part 5 of 12** of the *Military Science, Rockets, Space, Fusion, and Mars* reference (plugin
> `military-space-rockets-and-fusion`), covering §17–§22 — mission architecture and the design cascade, power and thermal, communications and navigation, attitude control and EDL, human physiology and ISRU, and reliability. Sibling skills:
> `endeavour-military-theory-levels-of-war-and-deterrence` (§1–§3 — what military science is, the theoretical canon, the levels of war, and deterrence and nuclear strategy),
> `endeavour-logistics-doctrine-modern-conflict-and-the-law` (§4–§6 — force structure, logistics, doctrine, intelligence, procurement, modern conflict, and the law of armed conflict),
> `endeavour-rocket-equation-nozzles-engines-and-propellants` (§7–§10 — the rocket equation and staging, nozzle thermodynamics and the combustion chamber, turbomachinery and cooling, and propellants),
> `endeavour-orbits-ascent-structures-and-reentry` (§11–§16 — orbital mechanics, the ascent Δv budget, aerodynamic loads and structures, guidance and control, reentry physics, and failure physics),
> `endeavour-fusion-physics-confinement-and-engineering` (§23–§25 — fusion physics and the Lawson criterion, magnetic and inertial confinement, and why fusion is hard to engineer),
> `endeavour-satellites-flight-software-and-instruments` (§26–§28 — satellite design, types and orbits, flight software and FDIR, scientific instrumentation, and planetary protection),
> `endeavour-the-martian-environment-and-in-situ-resources` (§29–§30 — the Martian environment as engineering parameters, and Mars resources and ISRU),
> `endeavour-mars-mission-design-and-settlement` (§31–§32 — Mars launch windows, EDL, communications and surface power, and settlement),
> `endeavour-terraforming-warming-and-the-magnetic-field-problem` (§33–§35 — terraforming theory and the habitability thresholds, atmospheric thickening and warming, and the magnetic field problem),
> `endeavour-ecopoiesis-oxygen-timelines-and-ethics` (§36–§38 — ecopoiesis and the oxygen problem, timelines and paraterraforming, and ethics and the Venus comparison),
> `endeavour-reference` (§39–§40 — the glossary spanning all six parts, and the further reading),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. The physics here is durable; specific mission figures, demonstrated
> hardware performance and agency dose limits are as of the source and do drift.

Three constraints generate every mission design, and everything below is downstream of them.
**Mass is the currency, and everything converts to it** — power converts to mass (arrays,
radioisotopes, radiators), data rate converts to mass (antenna, power), reliability converts to mass
(redundancy), crew time converts to mass (consumables); you are always spending the same budget.
**Distance imposes latency and darkness** — light-time makes teleoperation impossible beyond the
Moon, forcing autonomy, and inverse-square makes both sunlight and signal scarce. And **for crewed
deep space the binding constraint is not propulsion but human physiology** — radiation dose and
microgravity deconditioning bound mission duration more tightly than Δv does.

---

## §17 Mission architecture and the design cascade

The design cascade flows downward while mass flows upward, and the loop closes only by iteration:

    science/mission objectives → measurement requirements → instrument selection
      → pointing, power, data volume, thermal requirements → bus sizing
      → mass and volume → launch vehicle and trajectory → constrains everything above

> **THE CHARACTERISTIC MISTAKE IS TREATING THIS AS A WATERFALL.** It converges only if you carry
> margins and re-run the loop when any element grows. A cascade run once, forward, with no reserve
> produces a design that cannot absorb the first instrument that gains a kilogram.

### The architecture trades

| Trade | Poles |
|---|---|
| Flyby / orbiter / lander / rover / sample return | Cost and risk rise steeply; so does science return per target |
| Solar vs. radioisotope | Decided largely by heliocentric distance and duty cycle |
| Chemical vs. electric propulsion | Time versus propellant mass |
| Direct vs. gravity assist | Δv versus flight time and window rigidity |
| Store-and-forward vs. direct-to-Earth | Relay orbiters transform surface data return |

### Windows, porkchops and assists

**Launch windows** are set by planetary geometry. The Mars synodic period is ≈ 25.6 months — miss
the window and you wait over two years, which is the single hardest scheduling constraint in
planetary exploration; the Mars-specific consequences for crewed transfers are at §31 →
`endeavour-mars-mission-design-and-settlement`.

**Porkchop plots** — contours of C₃ (launch energy) and arrival v_∞ over departure and arrival
dates — are the working tool of mission design.

**Gravity assists** buy Δv at the cost of rigidity and flight time. Cassini's VVEJGA
(Venus-Venus-Earth-Jupiter) took ~7 years to Saturn; direct would have needed a launch vehicle that
did not exist. **Assists do not just save propellant — they enable missions outright.** The
underlying two-body relations, the Oberth effect and plane-change costs are at §11 →
`endeavour-orbits-ascent-structures-and-reentry`.

## §18 Spacecraft power and thermal control

A spacecraft is a **bus** (the supporting infrastructure — power, thermal, attitude control,
propulsion, communications, command and data handling, structure) plus a **payload** (the instrument
or communication package the mission exists for); the split itself, and the orbit regimes it gets
designed into, are at §26 → `endeavour-satellites-flight-software-and-instruments`. This section
covers the first two subsystems.

### Power

**Solar flux scales as 1/r², and this single fact partitions the solar system.** At Mars (1.52 AU),
590 W/m² — 43% of Earth. At Jupiter (5.20 AU), 50 W/m². Solar becomes impractical roughly beyond
Jupiter; Juno flies enormous arrays and is the outer limit. Beyond that, radioisotope power is not a
preference, it is the only option.

- **RTGs.** ²³⁸Pu, 87.7-year half-life, thermoelectric conversion at only **~6–7% efficiency**.
  MMRTG ≈ **110 W electrical at BOL** from ~2,000 W thermal, decaying ~1.6%/yr. The binding
  constraint is **plutonium supply, not engineering**. The waste heat is a feature — RTG thermal
  output keeps spacecraft warm in the outer solar system.
- **Batteries.** Li-ion at ~100–250 Wh/kg, sized to eclipse duration and peak load, with
  depth-of-discharge traded against cycle life. A LEO spacecraft sees **~16 eclipses/day — about
  90,000 cycles over 15 years**, which forces shallow DoD.
- **Fission.** Kilopower/KRUSTY demonstrated the 1–10 kW class, for surface power where solar duty
  cycle fails: **a lunar night is 14 Earth days, and no practical battery bridges it.**

### Thermal

In vacuum there is no convection. Heat moves by conduction and radiation only, and **radiation is
the only path off the vehicle**:

    Q_rad = εσA(T⁴ − T_sink⁴)

> **THE T⁴ IS BRUTAL.** A radiator at 300 K rejects ~460 W/m²; at 200 K, only ~91 W/m². Rejecting
> heat from a cold instrument therefore costs area out of all proportion to the wattage, which is
> why cryogenic payloads are a structural and geometric problem, not a plumbing one.

The **α/ε ratio** — solar absorptivity over infrared emissivity — is the primary design knob, which
is why thermal control is largely a **coatings** problem. **MLI blankets** (10–30 layers of
aluminized Mylar, effective emissivity ~0.01–0.03) are the single most effective thermal component
on most spacecraft.

The extremes are what break designs. JWST needs its instruments below ~40 K, achieved with a
tennis-court-sized sunshield giving ~300 K of gradient across five layers. Parker Solar Probe
survives ~1,400 °C on a carbon-composite shield while the bus stays near room temperature. The lunar
surface swings ~120 °C to −170 °C, and permanently shadowed craters sit near 25–40 K — colder than
Pluto's surface.

## §19 Communications, navigation, and autonomy

### The link budget

    P_r = P_t + G_t + G_r − L_fs − L_other

Path loss scales as d², so **data rate falls as 1/d²**. Mars at opposition versus conjunction varies
by ~7× in distance — about 17 dB. **Coding buys enormous margin:** turbo and LDPC codes operate
within ~1 dB of the Shannon limit, against the ~9 dB gap of uncoded BPSK — an order of magnitude in
effective data rate for free, and the reason deep space missions return anything at all.

> **THE NUMBERS THAT SHOW THE PROBLEM.** Voyager 1 at ~24 billion km returns ~160 bit/s on a 3.7 m
> dish with 23 W. New Horizons at Pluto returned ~1–2 kbit/s and took **16 months** to downlink the
> encounter data. Data volume, not instrument capability, is frequently the limiting factor for
> outer-planet science. And the Deep Space Network (Goldstone, Madrid, Canberra — 120° apart for
> continuous coverage) is **oversubscribed**, a real and under-appreciated constraint on mission
> planning.

**Light-time**, one-way: Moon 1.3 s (teleoperation marginal); Mars 3–22 min (teleoperation
impossible); Jupiter 33–53 min; Voyager 1 ~23 hours. Round-trip to Mars exceeds 40 minutes at
conjunction. This is the single reason surface robots must be autonomous and why EDL must be
entirely self-contained — **the spacecraft has landed or crashed before Earth knows it entered.**

**Relay architecture.** Mars surface missions overwhelmingly return data via orbiters rather than
direct-to-Earth, because an orbiter passes overhead at ~400 km instead of 200 million, and the 1/d²
advantage is astronomical. The Mars relay fleet and the conjunction blackout are at §31 →
`endeavour-mars-mission-design-and-settlement`.

### Navigation

Three complementary measurement types, plus one optical. **Doppler** gives line-of-sight velocity,
precise to ~0.1 mm/s. **Ranging** gives round-trip time — metres at planetary distance. **Delta-DOR**
has two stations observe the spacecraft and a quasar alternately, and differencing removes common
errors to give plane-of-sky position to **nanoradians**. **Optical navigation** — imaging the target
against background stars — is essential for approach and for small bodies where the ephemeris is
poor.

### Autonomy

Autonomy is not a nicety at distance; **it is forced by light-time.** **Safe mode** — power-positive,
thermally stable, Earth-pointed, awaiting instructions — is entered by every deep space mission, and
the design question is whether it can survive there indefinitely. **Command loss timers** reconfigure
after N days without a command, which has saved missions whose primary receivers failed. And **fault
protection that misfires is itself a hazard**: a spurious safe-mode entry during a critical event can
lose the mission. The detect/isolate/recover machinery that implements all of this, and the rules for
not recovering into the fault, are at §27 → `endeavour-satellites-flight-software-and-instruments`.

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

## §21 Human physiology, life support, and ISRU

> **A MARS MISSION EXCEEDS NASA'S RADIATION DOSE LIMIT.** NASA's current career limit is **600 mSv**
> effective dose. Estimates based on two 180-day transits plus ~500 days on the surface put the dose
> **near 1,000 mSv — above the limit.** This is not a margin problem to be engineered away at the
> edges; it is the mission, stated as a number.

Two sources, with opposite characters. **GCR** is continuous, high-energy heavy ions, hard to shield
because they produce secondary particle showers — the dominant **chronic** risk. **SPE** is sporadic,
proton-dominated and potentially **acute** — the reason a storm shelter is required. And a perverse
coupling: **solar maximum brings more SPE risk but suppresses GCR.** Solar minimum is
safer for acute events and worse for chronic dose. Surface dose measurements and regolith shielding
are at §29 → `endeavour-the-martian-environment-and-in-situ-resources`.

**Microgravity effects.** Bone loss ~1–1.5% per month in weight-bearing bone, not fully recovered
post-flight. Muscle atrophy, cardiovascular fluid shift, orthostatic intolerance.

**SANS (Spaceflight Associated Neuro-Ocular Syndrome)** is the constraint people underestimate —
optic disc oedema, posterior globe flattening, choroidal folds, hyperopic shifts up to 1.5
dioptres, affecting **roughly 70% of astronauts on missions over six months**, with no terrestrial
equivalent. **The underlying aetiology is not understood.** SANS is why "we've done a year on ISS, so
Mars is fine" does not follow — a round-trip Mars mission is 2–2.5 years, well beyond any flown
experience.

### ECLSS and closure

Functions: atmosphere pressure and composition, CO₂ removal, O₂ generation, water recovery, waste
management, humidity, fire detection, trace contaminant control.

On ISS: O₂ by water electrolysis; CO₂ removal by molecular sieve; a **Sabatier reactor (CO₂ + 4H₂ →
CH₄ + 2H₂O) recovering ~50% of the oxygen loop**; water recovery up to **~93%** from urine, sweat
and condensate.

**The gap between 93% and 98% is where the engineering difficulty lives.** At 5 kg/person/day of
consumables, a 1,000-day Mars mission for four people needs **20 tonnes open-loop**. Closure ratio is
the single biggest lever on crewed mission mass; what a permanent settlement needs beyond these
figures is at §32 → `endeavour-mars-mission-design-and-settlement`.

### ISRU — MOXIE proved the principle

MOXIE on Perseverance was the first demonstration of ISRU on another planet: a **15 kg** instrument
performing solid-oxide electrolysis of atmospheric CO₂ at **800 °C**, producing **12 g of oxygen per
hour at ≥98% purity**.

**The energy cost is the real constraint on scaling: ~30–70 kWh per kilogram of oxygen.** A Mars
ascent vehicle needs tens of tonnes of oxygen; at even 15 kWh/kg, 30 tonnes is **~450 MWh** — which
is a power plant, not an instrument, and is why surface fission keeps appearing in Mars
architectures. Both figures are the source's, and **15 kWh/kg is below the 30–70 kWh/kg range it
gives one sentence earlier** — not at its floor — so **~450 MWh understates the plant**: the same
30 tonnes at the stated range is **900–2,100 MWh**. Reworking it only strengthens the section's
point, because the power plant gets bigger. The full mine-to-methalox chain is at §30 →
`endeavour-the-martian-environment-and-in-situ-resources`.

**Why ISRU matters at all:** the rocket equation means propellant for the return trip, launched from
Earth, costs enormously more than its own mass at departure. **Making it at the destination breaks
the exponential.**

## §22 Reliability, margins, and the failures that teach them

Standard margins carried through design phases:

| Quantity | Margin |
|---|---|
| Mass | 30% at concept → 5–10% at CDR |
| Power | 20–30% early |
| Data rate / volume | ~25% |
| Δv | 5–10%, plus explicit statistical margin |

**The mass margin exists because mass always grows, and a programme that spends its margin early has
no options later.**

**Redundancy** comes in three forms: **block** (a whole second string), **functional** (a different
subsystem achieves the same end), and **cross-strapping**. Watch **common-cause failure** — two
identical units with the same design flaw fail identically, so two of them is not two chances.
**Deployments** (solar arrays, antennas, booms) are classic single-point failures: Galileo's
high-gain antenna never fully opened, forcing the entire mission onto the low-gain link.

The recurring lessons, each named with its actual cause:

- **Mars Climate Orbiter (1999)** — pound-force-seconds versus newton-seconds in a ground software
  interface. A units error.
- **Mars Polar Lander (1999)** — leg-deployment vibration read as touchdown; engines cut at
  altitude. A software response to an unanticipated sensor transient.
- **Ariane 501** — reused inertial software on a trajectory it was not designed for.
- **Beagle 2** — incomplete solar panel deployment blocked the antenna; no telemetry, so no
  diagnosis for a decade.

> **TEST AS YOU FLY.** Most of the above are failures of that principle. The organizational pattern
> by which a known anomaly becomes an accepted one — normalization of deviance, with Challenger and
> Columbia as its canonical cases — is at §16 → `endeavour-orbits-ascent-structures-and-reentry`.
