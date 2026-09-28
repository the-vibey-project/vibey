---
id: skill-31-method-1d177372ef
purpose: 31 method
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-reference/SKILL.md
requires: ["skill-30-quick-reference-7334165f39"]
links: []
---

## §31. Method

**§1–§25 → `hw-bottlenecks-cpu-memory-gpu-and-storage`, `hw-interconnect-power-thermals-and-networking`, `hw-specifying-assembly-firmware-tuning-and-benchmarking`, `hw-datacentre-facility-power-cooling-and-efficiency`, `hw-datacentre-network-storage-failure-and-operations` rests on settled computer architecture and mature facility practice** — **the
memory hierarchy, Amdahl's law, thermal paths, UPS topologies, Tier definitions, leaf-spine
networking and the failure literature.** ⚠️ **None needed verification; the processor-memory
gap has been the central architectural fact for thirty years.**

**Two searches were run in August 2026**, on **data centre power constraints** and **rack
power architecture** — ⚠️ **the first because §1 → `hw-bottlenecks-cpu-memory-gpu-and-storage`'s bottleneck migration reached a new step
that changes what can be built at all, the second because §17 → `hw-datacentre-facility-power-cooling-and-efficiency`'s distribution chain is being
redesigned in a way that directly applies an electromagnetism reference's I²R physics.**

**Confidence.** **High** in §3 → `hw-bottlenecks-cpu-memory-gpu-and-storage` and §8 → `hw-interconnect-power-thermals-and-networking`, which are the sections I'd most want read.
⚠️ **The latency ladder is the single most useful thing here — a main memory access costs
hundreds of cycles, during which a core could have executed hundreds of instructions, and
that fact explains most real-world performance behaviour.** ⚠️ **§8 → `hw-interconnect-power-thermals-and-networking`'s identity between power
draw and cooling requirement is the second, because it scales unchanged from a desk fan to
a hundred-megawatt facility and it is why §26.1 and §26.2 are the same story viewed at
different points in the chain.** **§7 → `hw-interconnect-power-thermals-and-networking`'s transient-response point is the practical one that
saves the most grief in custom builds.**

**Moderate-to-high** on §26.1. ⚠️ **The structural claim — that grid interconnection and
heavy electrical equipment have displaced chips as the binding constraint — is consistent
across every source and is corroborated by the equipment lead-time data, which is a
physical fact rather than a forecast.** ⚠️ **The specific figures (2,600 GW queue, 410 GW
ERCOT, 128/144-week transformer lead times) are cited to LBNL, Wood Mackenzie and grid
operators through secondary reporting and I've attributed them.** **⚠️ I'd treat the demand
PROJECTIONS with more scepticism than the constraint data — this sector's forecasts have
been revised repeatedly, and most of the commentary comes from developers and investors who
benefit from a scarcity narrative.**

**High** on §26.2's physics, which is checkable arithmetic: ⚠️ **120 kW at 48 V is over
2.5 kA, and NVIDIA's own figures of up to 200 kg of copper busbar per megawatt rack and 64U
of power shelves at 54 VDC are the reason the architecture must change.**
⚠️ **The density roadmap figures are vendor projections and I've marked them reported.**
**⚠️ The most useful corrective in that section is the analysis noting 800 VDC is NOT yet
required — the 2026–27 generations at 180–220 kW remain within three-phase AC's reach, so
current adoption is voluntary future-proofing rather than a forced response.** ⚠️ **Nearly
every source here sells the transition, which is exactly why that dissenting point is worth
carrying.**
