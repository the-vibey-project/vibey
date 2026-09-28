---
id: skill-5-radiation-effects-in-software-terms-305dc6a1b1
purpose: 5 radiation effects in software terms
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-processors-radiation-and-real-time/SKILL.md
requires: ["skill-4-flight-processors-dfbd026167"]
links: ["skill-6-real-time-discipline-67ad62c7a8"]
---

## §5. Radiation Effects, in Software Terms

**[DURABLE] Physics is in a space-exploration reference §11. Here's what the software must
do about it.**

| Effect | Software response |
|---|---|
| **SEU** — bit flip in memory or register | **EDAC + scrubbing** (§5.1) |
| **SEFI** — functional interrupt, device hangs | Watchdog, power-cycle, reconfigure |
| **SEL** — latchup, potentially destructive | ⚠️ **Current-limit detection and rapid power cycling — this is a hardware/software co-design** |
| **TID** — cumulative degradation | Margin, and end-of-life parameter drift |
| **MBU** — multiple bits in one word | ⚠️ **Defeats simple SECDED — needs interleaving** |

**5.1 EDAC and scrubbing.** **SECDED** (single error correct, double error detect) Hamming
codes on memory, plus ⚠️ **a background scrubber task that walks all of memory
periodically, reading and rewriting to correct single-bit errors before a second flip
makes them uncorrectable.** **The scrub period must be short relative to the expected
double-error accumulation time** — that's the actual design calculation, and it depends on
orbit.

**5.2 Redundancy in software**: **TMR** (triple modular redundancy with voting — in
hardware, or in software for critical variables), **checksummed critical data structures**,
**periodic recomputation and comparison**, and **⚠️ "self-checking pairs"** where two
dissimilar computations must agree.

**5.3 ⚠️ Defensive coding that is specific to this domain:**
- **Validate state variables on read**, not just on write — ⚠️ **the value may have changed
  since you wrote it, with no code executing.**
- **Enumerations with wide separation** in bit patterns, so a single flip doesn't turn one
  valid state into another valid state. **Never use 0/1/2/3 for a mode variable in
  radiation.**
- **Checksum code segments and compare periodically** — ⚠️ **instruction memory corrupts
  too.**
- **Bound every loop** (Power of 10 rule 2) so a corrupted counter cannot hang the system.
- **⚠️ Assume any single reading is suspect**; require consistency across time or sensors.

---
