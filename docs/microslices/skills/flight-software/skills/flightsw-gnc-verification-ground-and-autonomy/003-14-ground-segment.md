---
id: skill-14-ground-segment-6abbbf1445
purpose: 14 ground segment
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-gnc-verification-ground-and-autonomy/SKILL.md
requires: ["skill-13-verification-and-validation-d6a52a674f"]
links: ["skill-15-autonomy-and-onboard-ai-86c34ad723"]
---

## §14. Ground Segment

**⚠️ Ground software is where most of the code is, and it gets a fraction of the attention.**

**Components**: mission planning and sequence generation (⚠️ **with constraint checking —
the ground tool that catches an illegal command sequence is worth more than the onboard
check that rejects it**), command generation and uplink, **telemetry processing,
decommutation and archiving**, monitoring and alarm display, trending and anomaly
analysis, **simulators**, and flight dynamics.

**Open source worth knowing**: **NASA OpenMCT** (mission control visualization),
**COSMOS/OpenC3** (command and control), **Yamcs** (mission control framework),
**SatNOGS** (ground station network). ⚠️ **The commercial and institutional systems are
mostly bespoke, which is exactly the reuse problem cFS solved on the flight side and
nobody has fully solved on the ground side.**

**⚠️ Operational practice**: **procedures for everything**, **anomaly response teams and
on-call rotations**, **the command approval chain** (⚠️ **two-person review for hazardous
commands is standard for good reason**), and **long-term archiving in PDS** for planetary
missions.

---
