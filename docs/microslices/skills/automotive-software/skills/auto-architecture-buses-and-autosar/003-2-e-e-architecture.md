---
id: skill-2-e-e-architecture-71d8441289
purpose: 2 e e architecture
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-architecture-buses-and-autosar/SKILL.md
requires: ["skill-1-what-makes-it-different-b38eb12c4f"]
links: ["skill-3-buses-and-networking-a343fc18a6"]
---

## §2. E/E Architecture

### 2.1 The evolution
```
DISTRIBUTED     one ECU per function. ⚠️ 100+ ECUs, kilometres of harness,
                a CAN bus per domain, no central compute
      ↓
DOMAIN          controllers per functional domain (powertrain, chassis, body,
                infotainment, ADAS), gateway between them
      ↓
ZONAL           ⚠️ ECUs grouped by PHYSICAL LOCATION (front-left, rear-right...),
                each zone controller aggregates local I/O and power,
                Ethernet backbone to central compute
      ↓
CENTRAL COMPUTE one or few HPC nodes running most functions; zones become
                smart I/O and power distribution
```
**⚠️ Why zonal wins on cost, and it isn't primarily about compute**: **the wiring harness
is among the heaviest and most expensive components in a car**, and it's assembled by
hand. **Grouping by location instead of function collapses harness length dramatically** —
one reported platform target is **>50% ECU reduction and ~40% wiring reduction.**

> **⚠️ GOTCHA — zonal does not remove complexity, it relocates it.** Experience from the
> first large-scale deployments is explicit: **the hardware simplifies and the software
> governance, system architecture and operational maturity demands go up.** ⚠️ **You have
> traded a wiring problem for a distributed-systems problem** — service discovery,
> timing across a network, resource contention on shared compute, and the need for
> hypervisor-level isolation between mixed-criticality functions.

### 2.2 Mixed criticality on shared compute
**⚠️ The central problem of central compute**: an ASIL-D braking function and an
infotainment app on the same SoC must not interfere. **Mechanisms**:
- **Hypervisor partitioning** (⚠️ **spatial and temporal isolation — the standard answer;
  QNX Hypervisor, PikeOS, Xen-based, vendor-specific**).
- **Separate MCU alongside the HPC** for the hard-real-time safety island —
  ⚠️ **very common: a big applications processor plus a lockstep safety MCU.**
- **Lockstep cores** (§6.4 → `auto-real-time-safety-and-cybersecurity`).

### 2.3 Power and E/E realities
**12 V** legacy, **48 V** increasingly for mild hybrid and high-current loads,
**400/800 V** traction. ⚠️ **Load dump, cold crank, and reverse polarity are the
transients every ECU must survive** — see an electrical-engineering reference §8.
**Quiescent current is a hard budget**: ⚠️ **a parked car must not flatten its battery in
weeks, so total sleep current across all ECUs is allocated in milliamps.**

---
