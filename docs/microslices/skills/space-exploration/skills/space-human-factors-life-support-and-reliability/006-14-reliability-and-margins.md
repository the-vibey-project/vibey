---
id: skill-14-reliability-and-margins-5545668b6a
purpose: 14 reliability and margins
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-human-factors-life-support-and-reliability/SKILL.md
requires: ["skill-13-planetary-protection-09eb27d8a3"]
links: []
---

## §14. Reliability and Margins

### 14.1 Margins

**[DURABLE] Standard practice, carried through the design phases:**
```
Mass       ⚠️ 30% at concept → 5–10% at CDR
Power      20–30% early
Data rate/volume  ~25%
Δv         5–10%, plus explicit statistical margin
Schedule and cost   ⚠️ historically the least respected and most exceeded
```
**⚠️ The mass margin exists because mass always grows**, and a programme that spends its
margin early has no options later (§1.3 → `space-mission-architecture-and-trajectory`).

### 14.2 Reliability

**Redundancy**: **block** (a whole second string), **functional** (a different subsystem
achieves the same end), **cross-strapping**. **⚠️ Watch common-cause failure** — two
identical units with the same design flaw fail identically.

**Single-point failures**: enumerated, and each either eliminated or formally accepted.
⚠️ **Deployments (solar arrays, antennas, booms) are classic SPFs** — Galileo's high-gain
antenna never fully opened, forcing the entire mission onto the low-gain link and a
heroic data-compression retrofit.

**⚠️ The recurring lessons from failures worth internalizing:**
- **Mars Climate Orbiter (1999)** — pound-force-seconds versus newton-seconds in a ground
  software interface. ⚠️ **A units error in an interface, not a physics error.**
- **Mars Polar Lander (1999)** — leg-deployment vibration read as touchdown; engines cut at
  altitude. ⚠️ **A software response to an unanticipated sensor transient.**
- **Ariane 501** — reused inertial software on a trajectory it wasn't designed for, in a
  computation not even needed after liftoff. ⚠️ **Reuse without re-validation.**
- **Beagle 2** — reached the surface and partially deployed; ⚠️ **incomplete solar panel
  deployment blocked the antenna. No telemetry, so no diagnosis for a decade.**
- **⚠️ Test as you fly.** Most of the above are failures of that principle.
