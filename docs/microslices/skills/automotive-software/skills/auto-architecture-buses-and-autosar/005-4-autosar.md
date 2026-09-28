---
id: skill-4-autosar-c351c3177b
purpose: 4 autosar
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-architecture-buses-and-autosar/SKILL.md
requires: ["skill-3-buses-and-networking-a343fc18a6"]
links: []
---

## §4. AUTOSAR

**⚠️ AUTOSAR exists to let an OEM integrate software from many suppliers.** Understand it
as an interface standard for an org chart, and its design choices stop looking arbitrary.

### 4.1 Classic Platform
**For deeply embedded, hard-real-time, safety-critical ECUs on microcontrollers.**
```
Application Layer      Software Components (SWCs) — portable, hardware-agnostic
─────────────────────
RTE (Runtime Env.)     ⚠️ generated glue; SWCs talk only through this
─────────────────────
BSW (Basic Software)   Services / ECU Abstraction / MCAL
─────────────────────
Microcontroller
```
**⚠️ The point of the RTE**: an SWC declares ports and interfaces; the RTE generates the
plumbing. **Whether the partner SWC is on the same core, another core, or another ECU
across CAN is a configuration decision, not a code change.** That relocatability is the
whole value proposition.
**MCAL** is the vendor-supplied hardware abstraction. **OS is OSEK/VDX-derived** —
⚠️ **statically configured, priority-based, no dynamic task creation** (§5 → `auto-real-time-safety-and-cybersecurity`).
**⚠️ Configuration is enormous and tool-driven** (ARXML), which is why AUTOSAR work is so
tooling-dependent.

### 4.2 Adaptive Platform
**For high-performance ECUs: POSIX-based (typically Linux or QNX), C++14+, dynamic.**
- **⚠️ Service-oriented via ara::com over SOME/IP or DDS** — dynamic discovery.
- **Dynamic deployment**: applications can be installed, updated and started at runtime.
- **⚠️ Designed for ADAS, infotainment, and central compute — where compute is plentiful
  and requirements change over the vehicle's life.**

> **⚠️ GOTCHA — Classic and Adaptive coexist, and will for a long time.** They are not
> a migration path where one replaces the other. **Classic remains correct for hard
> real-time, low-power, ASIL-D control on a microcontroller; Adaptive is correct for
> high-compute, updatable, service-oriented functions.** **A modern vehicle runs both**,
> often with a vendor platform unifying them, and **anyone telling you Adaptive replaces
> Classic is selling something.**

**⚠️ AUTOSAR's genuine criticisms are worth knowing**: configuration complexity is
enormous, tooling is expensive and vendor-locked, the generated code is hard to debug,
and iteration is slow. **Some SDV-focused players — Tesla most visibly — largely
bypassed it**, which is only possible if you control the whole stack rather than
integrating a supply chain (§14 → `auto-process-testing-domains-and-supply-chain`).
