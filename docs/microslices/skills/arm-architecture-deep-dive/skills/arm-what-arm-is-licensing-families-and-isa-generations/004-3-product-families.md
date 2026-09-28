---
id: skill-3-product-families-ae81221de2
purpose: 3 product families
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-what-arm-is-licensing-families-and-isa-generations/SKILL.md
requires: ["skill-2-the-licensing-model-d02c74977b"]
links: ["skill-4-isa-generations-f87ab89edf"]
---

## §3. Product Families

**⚠️ Cortex-A** — application processors. ⚠️ **The little/middle/big naming (A5xx / A7xx) and
the X-series as the maximum-performance line.**
**⚠️ Cortex-R** — real-time, ⚠️ **MPU rather than MMU, deterministic interrupt latency, used
in storage controllers, modems and automotive.**
**⚠️ Cortex-M** — microcontrollers (§21 → `arm-cortex-m-toolchain-porting-and-performance`), ⚠️ **the volume leader by unit count by an
enormous margin.**
**⚠️ NEOVERSE** — infrastructure: ⚠️ **V-series (maximum per-core performance), N-series
(balanced, throughput per watt), E-series (efficiency/edge).** ⚠️ **This is where the
datacentre story lives** (§26.2 → `arm-reference`).
**⚠️ Ethos** NPUs, **Mali/Immortalis** GPUs, ⚠️ **CoreLink and CoreSight** for interconnect
and debug.
**⚠️ The naming is genuinely confusing** — ⚠️ **architecture version (ARMv9), core name
(Cortex-A720), and product tier are three independent things, and a new core does not imply
a new architecture version.**

---

# PART II — THE ARCHITECTURE
