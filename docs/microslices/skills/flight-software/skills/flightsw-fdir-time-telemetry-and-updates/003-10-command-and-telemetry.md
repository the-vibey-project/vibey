---
id: skill-10-command-and-telemetry-2986c1116f
purpose: 10 command and telemetry
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-fdir-time-telemetry-and-updates/SKILL.md
requires: ["skill-9-time-and-clocks-d1af8fec66"]
links: ["skill-11-data-handling-and-in-flight-update-6dd1c92e56"]
---

## §10. Command and Telemetry

**[DURABLE] CCSDS is the international standard set, and it is genuinely worth following
rather than inventing.**

**The stack:**
```
Application:  ⚠️ Space Packet Protocol (CCSDS 133.0-B) — APID identifies the destination
Transfer:     TM/TC Space Data Link, or AOS for higher rates
Coding:       Reed-Solomon, convolutional, ⚠️ turbo/LDPC (near-Shannon)
Physical:     RF, per a space-exploration reference §5
```

**Telecommand**: **CLTU** framing, ⚠️ **COP-1 (Communications Operations Procedure)
providing sequence-controlled, guaranteed-delivery command transfer** — with a **FARM/FOP
state machine** that is a genuine source of operational subtlety.

**⚠️ Command design principles that matter operationally:**
- **Idempotent where possible** — ⚠️ **a retransmitted command should not do the thing
  twice.**
- **Two-stage arm/fire for hazardous commands** (deployments, pyros, engine starts).
- **Validate before execute**: checksum, authenticate (⚠️ **command authentication is now
  standard, and CCSDS SDLS provides it — an unauthenticated uplink is a hijack risk**),
  and range-check every parameter.
- **⚠️ Reject, don't clamp.** Silently clamping an out-of-range parameter hides the ground
  error that produced it.
- **Absolute and relative time-tagged sequences** — the backbone of deep space ops.

**Telemetry**: **housekeeping** (periodic state), **event/EVR messages** (⚠️ **the
spacecraft's log, and your only debugger**), **science**, **diagnostic dwell** (⚠️ **read
arbitrary memory addresses — indispensable for in-flight debugging**).

**⚠️ Design telemetry for the anomaly you haven't had yet.** The recurring operational
regret is insufficient telemetry to diagnose a fault after it occurs. **Budget bandwidth
for diagnostics, include mode and state transitions, and make everything you'd want during
a 3 a.m. anomaly call reachable without a patch.**

---
