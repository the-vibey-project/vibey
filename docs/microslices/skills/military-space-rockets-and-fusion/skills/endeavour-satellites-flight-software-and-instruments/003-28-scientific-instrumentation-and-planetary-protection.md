---
id: skill-28-scientific-instrumentation-and-planetary-protection-9b8c0e136b
purpose: 28 scientific instrumentation and planetary protection
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-satellites-flight-software-and-instruments/SKILL.md
requires: ["skill-27-flight-software-fdir-command-and-telemetry-and-in-flight-update-559741efc0"]
links: []
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
