---
id: skill-17-currency-and-contested-44cf86234f
purpose: 17 currency and contested
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-reference/SKILL.md
requires: []
links: ["skill-18-books-and-standards-a3163010e8"]
---

## §17. Currency and Contested

### 17.1 Contested

**⚠️ Rust versus C.** §3.2 → `flightsw-architecture-languages-and-standards`. **Neither position is silly.** The memory-safety argument is
strong precisely because the domain is unforgiving; the heritage-and-toolchain argument is
strong for the same reason. **Current honest position: partial adoption, non-critical
paths first, and watch the qualification story.**

**⚠️ cFS versus F Prime versus roll-your-own.** §2.2 → `flightsw-architecture-languages-and-standards`. Rolling your own is almost always
wrong now, ⚠️ **and "almost" is doing real work — very small, very short missions with
unusual constraints sometimes justify it.**

**⚠️ COTS versus rad-hard.** §4 → `flightsw-processors-radiation-and-real-time`. **Genuinely mission-dependent**: LEO smallsat versus
outer-planet flagship are different problems with different right answers.

**⚠️ How much autonomy.** §15 → `flightsw-gnc-verification-ground-and-autonomy`. More capability at distance, harder verification, and
fault protection that can itself cause failures (§8 → `flightsw-fdir-time-telemetry-and-updates`).

**⚠️ Linux in flight-critical roles.** Increasingly common for payload processing;
⚠️ **still contested for hard real-time control paths without partitioning.**

### 17.2 Verified August 2026

| Thing | Status | Decay risk |
|---|---|---|
| **cFS** | **v7.0.0 "Draco" (January 2026) added QNX** to OSAL alongside Linux, VxWorks, RTEMS. **Gov Alpha planned April 2026** — security, AI/ML, robotics, autonomy. **40+ NASA missions**, including Roman; **primary architecture for Lunar Gateway.** 2026 Symposium drew ~150 in person with cross-sector participation | Medium |
| **F Prime** | JPL, open source, component/typed-port/topology with autocoding. Flown on **Lunar Flashlight, NEA Scout, Ingenuity** | Low |
| **⚠️ HPSC** | Microchip **PIC64-HPSC**, rad-hard 64-bit **RISC-V** SoC, ~**2 TOPS INT8**, **240 Gbps TSN Ethernet switch**, supports **Linux, RTEMS, Xen**. **First "Hello Universe" and start of JPL functional/radiation/thermal/shock testing February 2026**; **May 2026 reports indicate ~500× current rad-hard processors** against a **100×** program goal. ⚠️ **Not spaceflight-qualified; no first mission named; samples to early-access partners** | **High** |
| **Incumbent processors** | **RAD750** remains the two-decade workhorse; **RAD5545** the quad-core successor; **GR740** the European counterpart | Low |
| **Rust** | ⚠️ **Adoption in safety-critical space still lacking**; research direction is **partial C-to-Rust rewrites**, not replacement. Teams adopting it train on the job. Described in a 2026 assessment as the highest-leverage new language to learn for the domain | Medium |

---
