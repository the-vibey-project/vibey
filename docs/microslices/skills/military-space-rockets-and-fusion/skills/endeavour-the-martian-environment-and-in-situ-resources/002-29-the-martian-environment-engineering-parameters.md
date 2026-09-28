---
id: skill-29-the-martian-environment-engineering-parameters-34a90f1f1b
purpose: 29 the martian environment engineering parameters
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-the-martian-environment-and-in-situ-resources/SKILL.md
requires: ["skill-the-framing-for-part-vi-5fd3c02544"]
links: ["skill-30-mars-resources-and-in-situ-resource-utilisation-861d2a4f7b"]
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
