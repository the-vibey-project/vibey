---
id: skill-22-reliability-margins-and-the-failures-that-teach-them-6b6f5a2952
purpose: 22 reliability margins and the failures that teach them
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mission-architecture-and-spacecraft-subsystems/SKILL.md
requires: ["skill-21-human-physiology-life-support-and-isru-4840544458"]
links: []
---

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
