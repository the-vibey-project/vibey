---
id: skill-10-flight-controls-and-avionics-67c05081db
purpose: 10 flight controls and avionics
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-structures-aeroelasticity-and-avionics/SKILL.md
requires: ["skill-9-aeroelasticity-2131fc5f83"]
links: []
---

## §10. Flight Controls and Avionics

**Mechanical → hydraulic → fly-by-wire.**
**⚠️ FBW's real significance is not weight saving**: **it decouples the pilot's inceptor
from the surfaces, allowing envelope protection, relaxed static stability (§6 → `aero-performance-stability-and-propulsion`), and
gust-load alleviation.** ⚠️ **It also makes the software safety-critical in the formal
sense** — see a flight-software reference for DO-178C, redundancy and dissimilarity.

**⚠️ Control law philosophies differ and it matters operationally**: **Airbus uses hard
envelope protections the pilot cannot override in normal law; Boeing uses soft limits with
override authority.** ⚠️ **Both are defensible and the difference has been consequential in
accident analysis.**
**Redundancy**: triplex/quadruplex channels, dissimilar hardware and software, voting.
**⚠️ Air data** — pitot-static, AoA vanes. ⚠️ **Sensor failure is a recurring accident
theme: blocked pitot tubes (AF447) and erroneous AoA input driving an automatic system
(the MCAS accidents) both come back to trusting a degraded sensor.**
