---
id: skill-2-architecture-edea7adb23
purpose: 2 architecture
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-architecture-languages-and-standards/SKILL.md
requires: ["skill-1-what-makes-it-different-526bb94bc8"]
links: ["skill-3-languages-and-coding-standards-cfe8781196"]
---

## §2. Architecture

### 2.1 The layered pattern

**[DURABLE] Essentially every serious flight software stack looks like this:**
```
   Mission-specific applications  (science, payload ops, mission logic)
   ─────────────────────────────
   Reusable applications          (housekeeping, limit checking, stored commands,
                                   file management, telemetry output, scheduler)
   ─────────────────────────────
   Framework / executive          (message bus, event services, time services,
                                   table services, software bus)
   ─────────────────────────────
   OS abstraction layer           ⚠️ the portability seam
   ─────────────────────────────
   RTOS  (§7)
   ─────────────────────────────
   BSP / drivers / hardware       (§4)
```

**⚠️ The OS abstraction layer is the single highest-value architectural decision**, because
it lets you develop and test on Linux and deploy on an RTOS — which changes the economics
of testing completely (§13 → `flightsw-gnc-verification-ground-and-autonomy`).

**Message-passing over shared state**: components communicate via a **publish-subscribe
software bus** rather than shared memory. ⚠️ **This is not stylistic — it makes components
independently testable, makes the data flow inspectable in telemetry, and confines the
concurrency reasoning to the bus implementation** rather than spreading it across every
module.

### 2.2 The two frameworks worth knowing

**[VERSIONED in release detail, DURABLE in design.]**

**NASA cFS (core Flight System)** — ⚠️ **the de facto architectural standard, written in C**,
originally from Goddard. Structure: **OSAL** (OS abstraction), **PSP** (platform support
package), and **cFE** (core Flight Executive) providing event, time, table, file and
**software bus** services. It has flown **40+ NASA missions** from smallsats to flagships
including **Roman Space Telescope**, and is **the primary software architecture for Lunar
Gateway.**

⚠️ **v7.0.0 "Draco" (January 2026) added QNX** to the supported OS list alongside **Linux,
VxWorks and RTEMS.** A **cFS Gov Alpha release was planned for April 2026** adding security
capabilities, AI/ML integration, expanded robotics support and deeper autonomy.

**⚠️ Goddard's tagline is the whole argument: "Never build Flight Software from scratch
again."** The institutional pain being addressed is that every mission otherwise
reinvents command dispatching, telemetry, fault protection and housekeeping, **and gets it
wrong differently each time, with the lessons staying siloed per project.**

**JPL F Prime (F´)** — component-based with **typed ports** connected into a **topology**,
plus **autocoding tools** that generate components and topologies from model definitions.
Open source, C++. ⚠️ **Deployed on CubeSats, SmallSats, instruments and deployables** —
including **Lunar Flashlight and NEA Scout**, and **Ingenuity, the Mars helicopter.**

> **⚠️ GOTCHA — choosing between them is a real decision, not a preference.**
> A published comparison (built by implementing the same reference mission in both)
> found **they differ in design and in their assumptions about how a user extends them.**
> Broadly: **cFS is the mature, configuration-controlled choice with the deeper mission
> heritage and an active NASA CCB; F Prime is lighter, more modern in its
> model-driven autocoding, and better suited to small teams and instrument-scale
> deployments.** ⚠️ **Neither is wrong. Picking on vibes rather than on your mission class
> and team size is.**

### 2.3 The reusable applications
The set that recurs across every mission, and that the frameworks exist to stop you
rewriting: **command ingest and dispatch**, **telemetry output**, **stored command
sequencer** (⚠️ **absolute and relative time sequences — the backbone of deep space
operations**), **housekeeping**, **limit checker**, **memory manager and dwell**,
**file manager and CFDP** (§11 → `flightsw-fdir-time-telemetry-and-updates`), **checksum**, **health and safety**, and
**data storage/recorder management**.

---
