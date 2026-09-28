---
id: skill-1-what-makes-it-different-526bb94bc8
purpose: 1 what makes it different
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-architecture-languages-and-standards/SKILL.md
requires: ["skill-0-routing-1f30aeafea"]
links: ["skill-2-architecture-edea7adb23"]
---

## §1. What Makes It Different

**[DURABLE] The constraints, and why each inverts normal practice:**

| Constraint | Consequence |
|---|---|
| **No physical access, ever** | ⚠️ **Every failure must be diagnosable and recoverable remotely** |
| **Uplink is scarce and slow** | Patches are measured in kilobytes; §11 → `flightsw-fdir-time-telemetry-and-updates` |
| **Radiation corrupts memory** | ⚠️ **Assume your own state is wrong; scrub and check** (§5 → `flightsw-processors-radiation-and-real-time`) |
| **Hard real-time deadlines** | Determinism over throughput (§6 → `flightsw-processors-radiation-and-real-time`) |
| **Extreme reliability requirement** | Formal process, exhaustive review (§13 → `flightsw-gnc-verification-ground-and-autonomy`) |
| **Severely constrained compute** | ⚠️ **Flight CPUs are generations behind commercial** (§4 → `flightsw-processors-radiation-and-real-time`) |
| **Long lifetimes** | ⚠️ **20+ year missions on a toolchain that no longer exists** |
| **Test-as-you-fly is impossible** | You cannot put 1 g of gravity in orbit; §13.3 → `flightsw-gnc-verification-ground-and-autonomy` |

**⚠️ The cultural point that matters more than any technique**: flight software is written
under the assumption that **the reviewer, not the compiler, is the last line of defence**.
NASA's software classification (⚠️ **Class A "human-rated" through Class E**) drives the
required rigour, and **Class A software routinely costs $500–$1,000 per line** delivered.
That number sounds absurd until you price the alternative.

**⚠️ And the inversion worth internalizing**: in most software, you optimize for the
expected case and handle errors. **In flight software you design for the fault case, and
nominal operation is what happens when no fault fires.** §8 → `flightsw-fdir-time-telemetry-and-updates` is not a subsystem — it is the
organizing principle.

---
