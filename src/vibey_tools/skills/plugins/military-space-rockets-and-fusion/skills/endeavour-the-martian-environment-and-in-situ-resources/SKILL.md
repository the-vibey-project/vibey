---
name: endeavour-the-martian-environment-and-in-situ-resources
description: "Use when you need Mars as a set of engineering parameters — surface pressure and composition, why liquid water cannot exist stably at the surface, atmospheric density and scale height for EDL and rotorcraft, gravity and the ascent delta-v advantage, the sol and the eccentric orbit, temperature swings, the missing magnetic field, dust storms, surface radiation dose, and regolith chemistry including perchlorates — or when sizing in-situ resource utilisation from water ice, the CO₂ atmosphere and regolith. Part 8 of 12 of the Military Science, Rockets, Space, Fusion, and Mars reference."
---

# The Martian Environment and In-Situ Resources

> **Part 8 of 12** of the *Military Science, Rockets, Space, Fusion, and Mars* reference (plugin
> `military-space-rockets-and-fusion`), covering §29–§30 — Mars as a set of engineering parameters, and the resources you can make propellant, air, water and structure from. Sibling skills:
> `endeavour-military-theory-levels-of-war-and-deterrence` (§1–§3 — the theoretical canon, the levels of war, deterrence and nuclear strategy),
> `endeavour-logistics-doctrine-modern-conflict-and-the-law` (§4–§6 — force structure and logistics, doctrine, intelligence and procurement, modern conflict, and the law of armed conflict),
> `endeavour-rocket-equation-nozzles-engines-and-propellants` (§7–§10 — Tsiolkovsky and staging, nozzle thermodynamics and the chamber, turbomachinery, cycles and cooling, propellants and density impulse),
> `endeavour-orbits-ascent-structures-and-reentry` (§11–§16 — vis-viva and manoeuvres, the ascent budget, aerodynamic loads and structures, guidance, reentry physics and failure physics),
> `endeavour-mission-architecture-and-spacecraft-subsystems` (§17–§22 — mission architecture, power and thermal, comms and navigation, attitude control and EDL, human physiology, life support and ISRU, reliability),
> `endeavour-fusion-physics-confinement-and-engineering` (§23–§25 — fusion physics and the Lawson criterion, magnetic and inertial confinement, and why fusion is hard to engineer),
> `endeavour-satellites-flight-software-and-instruments` (§26–§28 — satellite design and orbits, flight software and FDIR, instrumentation and planetary protection),
> `endeavour-mars-mission-design-and-settlement` (§31–§32 — launch windows, Martian EDL, comms and surface power, habitats, mobility, ECLSS closure and the psychological challenge),
> `endeavour-terraforming-warming-and-the-magnetic-field-problem` (§33–§35 — terraforming theory and the three thresholds, atmospheric thickening and warming, the magnetic field problem),
> `endeavour-ecopoiesis-oxygen-timelines-and-ethics` (§36–§38 — ecopoiesis and the oxygen problem, timelines and paraterraforming, ethics and the Venus comparison),
> `endeavour-reference` (§39–§40 — the glossary for the whole reference, and the further reading),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. The planetary parameters here are measured and durable; the mission
> numbers, instrument results and architecture assumptions attached to them will drift.

## The framing for Part VI

Mars is the only body in the solar system where terraforming is physically plausible, and it is also
the most studied target for human settlement beyond Earth. Part VI covers the Martian environment in
engineering detail, the resources available for ISRU and settlement (both in this skill), the
mission design challenges Mars imposes (§31–§32 → `endeavour-mars-mission-design-and-settlement`),
and then the theory, methods, timelines and ethics of terraforming (§33–§35 →
`endeavour-terraforming-warming-and-the-magnetic-field-problem`, §36–§38 →
`endeavour-ecopoiesis-oxygen-timelines-and-ethics`). **The physics is real
and the engineering is genuinely hard.** The honest assessment the whole of Part VI is built on:
partial terraforming — paraterraforming — is tractable on century timescales, while full planetary
terraforming ranges from millennia to geological time depending on what you define as "done."

This skill is the parameter sheet. Everything downstream — entry mass, habitat wall thickness,
propellant plant sizing — is a consequence of the numbers below.

---

## §29 The Martian environment: engineering parameters

### Atmosphere

Mars has an atmosphere. This is both the most important fact about it and the most misleading one.
Surface pressure is approximately **610 Pa** — roughly **0.6% of Earth's sea-level 101,325 Pa**. For
comparison, that pressure is reached in Earth's atmosphere at about **50–55 km altitude**, in the
middle stratosphere.

| Constituent | Fraction | Note |
|---|---|---|
| CO₂ | ~95% | Partial pressure ~580 Pa; the ISRU feedstock — see §30 below |
| N₂ | 2.8% | ~17 Pa partial pressure — the scarce-nitrogen problem — see §30 below |
| Ar | 2% | Available as a buffer gas |
| O₂ | 0.2% | Not a usable oxygen source at this partial pressure |
| CO, water vapour, methane | traces | Methane's presence is debated and monitored |

> **LIQUID WATER CANNOT EXIST STABLY AT THE SURFACE**
> The CO₂ partial pressure is about **580 Pa**, below water's triple point at **611 Pa**. Ice
> sublimates directly to vapour. This is the single most important constraint on both biology and
> human activity, and it is why clearing the Armstrong limit is the first terraforming goal
> (§33 → `endeavour-terraforming-warming-and-the-magnetic-field-problem`). The atmosphere is thick
> enough to demand a heat shield for entry and to generate global dust storms, but too thin for
> parachutes alone to land large payloads, too thin for liquid water, and too thin for humans to
> survive without pressure suits. Every awkward feature of Mars operations descends from that one
> sentence.

**Density and scale height.** Surface density is about **0.020 kg/m³** against Earth's **1.225
kg/m³** — a factor of **~60**. Three consequences, each an engineering fact rather than a curiosity:

- **EDL** — parachute effectiveness scales with atmospheric density, which is the root of the
  Martian landing squeeze (§20 → `endeavour-mission-architecture-and-spacecraft-subsystems`;
  the Mars case in §31 → `endeavour-mars-mission-design-and-settlement`).
- **Wind loads** — fast winds carry little momentum, because the air is so thin. Martian gales are
  not a structural design driver in the way intuition suggests.
- **Rotorcraft** — Ingenuity's blades spin at **2,537 rpm** to generate lift in air that thin, and
  its maximum altitude was about **24 m**.

The **scale height is ~11 km**, similar to Earth's ~8.5 km, because lower temperature and lower
molecular weight partially compensate for lower gravity.

### Gravity, day, and year

| Parameter | Mars | Earth |
|---|---|---|
| Surface gravity | 3.71 m/s² (38% of Earth's) | 9.81 m/s² |
| Escape velocity | 5.03 km/s | 11.2 km/s |
| Δv to low orbit | ~3.8–4.2 km/s (Mars ascent vehicle) | ~9.4 km/s (LEO) |
| Day | 24 h 39 min 35.244 s (the sol) | — (the source gives only "remarkably close") |
| Year | 687 Earth days = 668.6 sols | — (Martian seasons run about twice Earth's length) |
| Axial tilt | 25.19° | 23.44° |
| Orbital eccentricity | 0.0934 | 0.0167 |

> **WHETHER 0.38 G PROTECTS IS UNKNOWN, AND THE DATA DOES NOT EXIST**
> It is not known whether 0.38 g is sufficient to prevent the bone loss, muscle atrophy,
> cardiovascular deconditioning and SANS observed in microgravity (§21 →
> `endeavour-mission-architecture-and-spacecraft-subsystems`). **No one has spent extended time in
> partial gravity.** There is no partial-gravity dataset to interpolate from, and treating 0.38 g as
> "probably enough" is an assumption, not a finding. Carry it as an open question in any crewed
> architecture that depends on it.

For engineering, low gravity is mostly a gift: structures can be lighter, landing is less demanding,
and ascent is far cheaper. The **~3.8–4.2 km/s to low Mars orbit against ~9.4 km/s for Earth LEO** is
the reason ISRU-produced propellant is so valuable — because propellant mass is exponential in Δv
(§7 → `endeavour-rocket-equation-nozzles-engines-and-propellants`), the return vehicle's mass at
launch from Mars is a fraction of what it would be from Earth, and making the propellant at the
destination breaks the exponential rather than paying it twice (§21 →
`endeavour-mission-architecture-and-spacecraft-subsystems`).

The sol at **24 h 39 min 35.244 s** is remarkably close to Earth's, which simplifies human circadian
adaptation and solar power scheduling. The year is **687 Earth days (668.6 sols)**, giving seasons
about twice Earth's duration, and the **25.19°** tilt gives familiar seasons — but they are
complicated by the **much more eccentric** orbit — **e = 0.0934** against Earth's **0.0167**. **Perihelion
occurs during southern summer**, so southern summer is shorter and hotter and southern winter longer
and colder, while northern seasons are milder. That asymmetry is one reason most landing sites are in
the north.

### Temperature

Surface temperatures range from about **−143 °C at the winter poles to +35 °C on summer equatorial
days**, with a global mean of about **−63 °C (210 K)**. The thin atmosphere has very low thermal
inertia, so **diurnal swings of 80–100 °C are routine** — a severe thermal control problem, because a
habitat or rover sees temperature cycles that would fatigue most materials. Convective heat loss is
minimal; the primary heat loss paths are radiation and conduction to the ground.

Permanently shadowed regions in craters near the poles may be as cold as **25–40 K** — colder than
Pluto's surface — preserving water ice deposits over geological time.

### No global magnetic field

Mars lost its dynamo roughly **4 billion years ago**. There is no global dipole field, only weak,
patchy **crustal** fields, strongest in the southern highlands. The practical consequences:

- **Atmospheric loss.** The solar wind impinges directly on the upper atmosphere and has been
  stripping it for billions of years. This is the **leading explanation** for why a Mars that once
  had a thicker atmosphere and liquid surface water now has the thin remnant we measure.
- **Radiation.** The surface receives the full galactic cosmic ray flux and solar particle events;
  the thin atmosphere provides negligible shielding against GCR.
- **For terraforming**, any atmosphere you build will be stripped again over timescales of millions
  of years — slow enough to be irrelevant for biological purposes, but a standing reminder that
  **Mars is not a stable container**. The problem is left unsolved; the three proposed responses and
  the honest loss-rate arithmetic are §35 →
  `endeavour-terraforming-warming-and-the-magnetic-field-problem`.

### Dust

Martian dust is fine — typically `<3 μm` — electrostatically charged, and ubiquitous.

- **Global dust storms occur roughly every 3–4 Mars years**, can envelope the entire planet for
  weeks to months, and **reduce solar irradiance at the surface by up to 97%**. This is the single
  largest threat to solar-powered surface missions: **Opportunity was lost after the 2018 global
  storm** cut power below survivable levels.
- **Settling between storms** causes gradual power degradation. That is what ended **Spirit**, and
  what Curiosity and Perseverance manage by waiting for wind events to clear panels.
- **Human health hazard.** The dust contains perchlorates (toxic to thyroid function), is fine
  enough to reach deep lung tissue, and its electrostatic charge makes it cling to spacesuits and
  habitat surfaces.

> **DUST MANAGEMENT IS A FIRST-ORDER ENGINEERING PROBLEM**
> Seals, airlocks, suit design and filtration are not housekeeping details for a permanent Martian
> presence — they sit alongside pressure and thermal control as things a habitat is designed around.
> Dust is also why solar is not the consensus baseline for sustained surface power
> (§31 → `endeavour-mars-mission-design-and-settlement`).

### Radiation at the surface

> **MARS SURFACE RADIATION IS NOT SAFE**
> Curiosity's **RAD** instrument measured the surface dose at **~0.21 mSv/day** on average, which
> projects to **~76 mSv/year**. The source gives **~40 mSv** for a 500-day surface stay from the
> surface environment alone — a figure that does not reconcile with its own daily rate, and is
> carried here as given rather than quietly recomputed — **plus ~300–400 mSv accumulated during
> transit**. The total for a Mars mission remains **above NASA's 600 mSv career limit** (§21 →
> `endeavour-mission-architecture-and-spacecraft-subsystems`).

The atmosphere provides some shielding — about **16 g/cm² of CO₂ equivalent at the datum** (mean
elevation) — which stops most solar particle events but **not GCR**. Regolith provides excellent
shielding: **1–2 m reduces GCR dose to near Earth-surface levels**. This is why most habitat designs
bury or berm modules with regolith: the material is free and already there, and it solves radiation
and thermal insulation simultaneously (§32 → `endeavour-mars-mission-design-and-settlement`).

### Regolith composition

Martian soil is **not** Earth soil. It has no organic component, no biological community, and no
structure formed by living processes — it is volcanic basaltic material modified by weathering,
oxidation and aeolian processes. That sterility is also what makes ecopoiesis slow
(§36 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics`).

| Component | Fraction by mass |
|---|---|
| SiO₂ | ~44% |
| Fe₂O₃ | ~18% (gives Mars its reddish colour) |
| Al₂O₃ | ~9% |
| MgO | ~8% |
| CaO | ~6% |
| SO₃ | ~6% |
| Perchlorate (ClO₄⁻) | **0.4–0.6%** — discovered by Phoenix, confirmed by Curiosity |

**Perchlorates are relevant for three reasons**, and all three matter to settlement design: they are
a potential **in situ oxygen source** (heating releases O₂); they **lower the freezing point of
water**, so brines can exist transiently on the surface; and they are **toxic to humans** through
thyroid hormone disruption.

Geotechnically the regolith is unusual: fine-grained at the surface (dust) with coarser material
beneath, in a near-vacuum with no moisture. **Bulk density is roughly 1,400–1,800 kg/m³**, but the
near-surface layer is loose and unconsolidated.

---

## §30 Mars resources and in-situ resource utilisation

### Water — the most valuable resource, in three reservoirs

| Reservoir | What is there | Accessibility |
|---|---|---|
| **Polar ice caps** | North cap primarily water ice, **~2 million km³** in the residual cap, with a seasonal CO₂ frost layer; south cap has a larger CO₂ component with water ice beneath | Concentrated, but polar |
| **Subsurface ice** | Present within **1–2 m** of the surface at mid-to-high latitudes; **above ~50° latitude likely within centimetres** | Confirmed by Phoenix (excavated ice, 2008) and by crater impacts exposing bright ice that then sublimated |
| **Hydrated minerals** | Clay minerals, sulfates and opaline silica in ancient terrains hold structurally bound water | Requires high-temperature processing |

**Mid-latitude subsurface ice is the accessible feedstock** — drill, excavate, melt, electrolyze.
Water yields hydrogen for propellant, oxygen for life support and propellant, and drinking water for
crews. It is also why landing-site selection is a resource decision as much as a safety one, and why
it collides with planetary protection's special regions
(§28 → `endeavour-satellites-flight-software-and-instruments`).

### The CO₂ atmosphere as feedstock

The atmosphere is ~95% CO₂ at 610 Pa. Thin, but a feedstock.

- **MOXIE demonstrated solid-oxide electrolysis** on Perseverance: **2CO₂ → 2CO + O₂**, producing
  pure oxygen directly from the atmosphere. Its demonstrated output and energy cost are §21 →
  `endeavour-mission-architecture-and-spacecraft-subsystems`.
- The **CO byproduct** can be used directly as a low-grade fuel, or processed via the **reverse
  water-gas shift (CO₂ + H₂ → CO + H₂O)** combined with electrolysis to produce methane by
  **Sabatier: CO₂ + 4H₂ → CH₄ + 2H₂O**.

**The full ISRU propellant chain for a Mars ascent vehicle:**

    mine water ice → electrolyze to H₂ and O₂ → Sabatier with atmospheric CO₂ → CH₄ + H₂O
        → split the water again → liquefy to LCH₄ and LOX

That is **methalox** — the same combination Starship uses, and a propellant whose Isp, bulk density
and common-bulkhead advantages are §10 → `endeavour-rocket-equation-nozzles-engines-and-propellants`
— produced **entirely from Martian resources**.

> **ENERGY, NOT CHEMISTRY, IS THE BINDING CONSTRAINT**
> Producing **~30 tonnes of O₂ and ~8 tonnes of CH₄** for a crewed ascent requires roughly **1–2 MWe
> continuously for 16–26 months**. None of the chemistry is exotic; the power plant is. This is why
> **fission surface power sits in the critical path of most Mars architectures**
> (§31 → `endeavour-mars-mission-design-and-settlement`) — the reaction is easy, the
> megawatt-months are not.

### Regolith for construction

Regolith is the most available construction material: **radiation shielding** (1–2 m bermed over
habitats), **thermal insulation** (low thermal conductivity), and **feedstock**. The techniques
investigated:

| Technique | How it works | What it needs |
|---|---|---|
| **Additive construction** | 3D printing regolith plus a binder, or sintering regolith | Concentrated solar or microwave energy, or an imported binder |
| **Compressed regolith blocks** | Natural cohesion of packed fines under pressure | Press energy only |
| **Sulfur concrete** | Molten sulfur as binder | Sulfur is available on Mars, and this requires **no water** |
| **Polymer-regolith composites** | Plastic matrix with regolith filler | Depends on producing plastics from atmospheric CO₂ |

**The structural challenge is that none of this is characterized.** Mars regolith in vacuum is not
well understood geotechnically, and any construction method must work **in 0.38 g, at 610 Pa external
pressure, and through temperatures that cycle to −60 °C nightly**. Treat published construction
concepts as concepts.

### Other resources

- **Nitrogen is scarce.** The atmosphere is only **2.8% N₂ at 610 Pa**, a partial pressure of about
  **17 Pa**. Nitrogen is essential for agriculture and fixing it from an atmosphere that dilute is
  energy-intensive. **This is one of the harder ISRU problems for self-sufficient settlement: the
  feedstock exists, but it is extremely dilute.** The same scarcity becomes the missing nitrogen
  cycle in any terraforming scenario (§36 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics`).
- **Argon** (2% of the atmosphere) is available as a buffer gas.
- **Metals** — iron, aluminium, titanium — are present in regolith but require high-temperature
  smelting: energy-intensive, but feasible with sufficient power.
- **No concentrated ore deposits have been identified.** Mining would start from bulk basaltic
  regolith, which has low ore grades. Every mass-production estimate for a Martian
  industrial base should be read against that.

---

## Cross-references

| You need | Go to |
|---|---|
| Launch windows, the Martian EDL squeeze and its one-tonne ceiling, comms and light-time, surface power, habitats, mobility, ECLSS closure | §31–§32 → `endeavour-mars-mission-design-and-settlement` |
| Radiation dose limits, GCR versus SPE, SANS and microgravity effects, MOXIE's demonstrated output and energy cost, why ISRU breaks the exponential, generic EDL and spacecraft power | §17–§22 → `endeavour-mission-architecture-and-spacecraft-subsystems` |
| The rocket equation and why propellant mass is exponential in Δv; methalox properties, density impulse and cryogenic handling | §7–§10 → `endeavour-rocket-equation-nozzles-engines-and-propellants` |
| The Armstrong limit and the three habitability thresholds, the mass problem, atmospheric thickening, warming strategies, and the magnetic field problem left unsolved | §33–§35 → `endeavour-terraforming-warming-and-the-magnetic-field-problem` |
| Ecopoiesis on sterile regolith, the oxygen problem, the missing nitrogen cycle, timelines and paraterraforming | §36–§38 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics` |
| Planetary protection categories and why special regions — where liquid water might exist — are effectively off-limits to non-sterilized hardware | §28 → `endeavour-satellites-flight-software-and-instruments` |
| Definitions of perchlorates, sol, ISRU, EDL and SANS, each with the section that explains it, plus the reading list | §39–§40 → `endeavour-reference` |
