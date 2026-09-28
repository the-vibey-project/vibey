---
id: skill-11-data-handling-and-in-flight-update-6dd1c92e56
purpose: 11 data handling and in flight update
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-fdir-time-telemetry-and-updates/SKILL.md
requires: ["skill-10-command-and-telemetry-2986c1116f"]
links: []
---

## §11. Data Handling and In-Flight Update

**Onboard storage**: ⚠️ **flash wear-levelling and radiation-induced corruption both
apply**; use **journaling or log-structured** approaches, checksum everything at rest, and
plan for **data prioritization** — when downlink is scarce, what gets dropped is a mission
decision that must be encoded.

**⚠️ CFDP (CCSDS File Delivery Protocol)** — reliable file transfer across a link with
**huge latency, intermittent connectivity, and asymmetric rates.** **Class 1
(unacknowledged) and Class 2 (acknowledged with retransmission).** It is the right answer
and it is worth using rather than rolling your own.

**⚠️ In-flight software update is the highest-stakes operation in the discipline.**
```
Design rules, each written in blood:
  1. ⚠️ The bootloader must be immutable, or dual-redundant with a golden image
  2. Uplink to inactive memory, verify checksum, THEN switch
  3. ⚠️ Automatic rollback on failure to check in after N minutes
  4. Never patch the receive chain and the patch mechanism at once
  5. ⚠️ Test the exact uplink product on the exact testbed configuration (§13.3)
  6. Patch granularity small enough to fit the uplink budget
```
**⚠️ A failed update that bricks the command receiver is unrecoverable and has ended
missions.** This is why rule 1 exists.

**⚠️ The counterexample worth knowing**: Voyager received a software patch in 2023–24 to
work around degraded memory **46 years after launch**, on a system whose original
engineers had retired or died. **That is only possible because the update path was
designed conservatively from the start.**
