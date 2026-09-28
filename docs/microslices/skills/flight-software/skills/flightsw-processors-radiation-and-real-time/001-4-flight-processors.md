---
id: skill-4-flight-processors-dfbd026167
purpose: 4 flight processors
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-processors-radiation-and-real-time/SKILL.md
requires: []
links: ["skill-5-radiation-effects-in-software-terms-305dc6a1b1"]
---

## §4. Flight Processors

**[VERSIONED — this is the area that moved most, and it changes what software is
possible.]**

**⚠️ The historical situation**: flight computers are generations behind commercial silicon
because radiation-hardening and qualification take years. **The BAE RAD750 — a PowerPC
derivative at ~200 MHz — has been the enduring workhorse for nearly two decades** and flies
on Curiosity, Perseverance, JWST and dozens more. **RAD5545** is the quad-core successor.
**GR740** (LEON4, SPARC) is the European counterpart.

**⚠️ HPSC changes the ceiling.** NASA's **High Performance Spaceflight Computing** program,
built by **Microchip** and productized as **PIC64-HPSC**, is a **radiation-hardened 64-bit
RISC-V SoC** with vector pipelines, a built-in **TSN Ethernet switch**, memory, and I/O.
Reported figures: **~2 TOPS INT8**, and it **supports Linux and RTEMS plus hypervisors
including Xen.**

**Status as of August 2026** — ⚠️ **and read this precisely, because coverage overstates
it**: the processor **sent its first "Hello Universe" message and began functional,
radiation, thermal and shock testing at JPL in February 2026.** JPL reported in May 2026
that testing is showing **indications of 500× the performance of current rad-hard flight
processors** — ⚠️ **against a program goal of 100×.**

> **⚠️ GOTCHA — the 500× figure is an early indication from an active test programme, not
> a flight result.** **HPSC has not completed spaceflight qualification, NASA has not named
> a first mission, and the programme page still places it in test and qualification.**
> Samples have gone to early-access partners. **Design against RAD750/RAD5545-class
> capability today; plan for HPSC as a future option.**

**⚠️ The architectural consequence if it qualifies**: onboard AI inference becomes
practical, which changes §15 → `flightsw-gnc-verification-ground-and-autonomy` from aspiration to engineering. **It also means Linux and
hypervisors on flight hardware become mainstream**, with all the mixed-criticality
questions that raises.

**The COTS trade**: commercial parts are vastly faster and cheaper but **radiation-soft**.
⚠️ **The smallsat approach — fly COTS, accept upsets, recover in software with watchdogs
and redundancy — is legitimate for LEO short-duration missions and dangerous for deep
space**, where total dose and no-repair change the calculus entirely.

---
