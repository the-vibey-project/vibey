---
id: skill-27-misconceptions-8676a99ab6
purpose: 27 misconceptions
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-reference/SKILL.md
requires: ["skill-26-what-s-live-checked-august-2026-3cee1e9388"]
links: ["skill-28-numbers-96247ab6bf"]
---

## §27. Misconceptions

| Misconception | Correction |
|---|---|
| More GHz means faster | ⚠️ **Instructions × CPI × cycle time. Three levers** (§2 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| The CPU is usually the bottleneck | ⚠️ **Most "slow" is memory-bound** (§3 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| Faster RAM is a big upgrade | ⚠️ **Capacity matters; speed is usually single-digit %** (§3 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| RAM runs at its advertised speed | ⚠️ **Not until you enable XMP/EXPO** (§12 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| RAM slot choice doesn't matter | ⚠️ **Wrong slots silently halve bandwidth** (§11 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| GPU TOPS figures are comparable | ⚠️ **Check the precision they're quoted at** (§4 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| GPUs are compute-limited | ⚠️ **Most real kernels are bandwidth-bound** (§4 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| RAID is a backup | ⚠️ **It survives drive failure, not deletion or ransomware** (§5 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| SSD benchmarks reflect sustained speed | ⚠️ **SLC cache exhaustion changes everything** (§5 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| Buy double the PSU wattage | ⚠️ **Efficiency peaks mid-load; transients matter more** (§7 → `hw-interconnect-power-thermals-and-networking`) |
| PSU cables are interchangeable | ⚠️ **Modular pinouts are NOT standardized** (§7 → `hw-interconnect-power-thermals-and-networking`) |
| Liquid cooling creates cooling | ⚠️ **It moves heat. The radiator still rejects to air** (§8 → `hw-interconnect-power-thermals-and-networking`) |
| Throttling means something is wrong | ⚠️ **It's the design. Better cooling IS performance** (§8 → `hw-interconnect-power-thermals-and-networking`) |
| Overclocking is free performance | ⚠️ **It consumes rated device lifetime** (§13 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`, §23 → `hw-datacentre-network-storage-failure-and-operations`) |
| Average FPS describes the experience | ⚠️ **1% and 0.1% lows are what you feel** (§15 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| Mean latency describes a service | ⚠️ **p99 is what users notice** (§15 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| Tier III means certified | ⚠️ **Usually claimed, rarely certified. Ask** (§16 → `hw-datacentre-facility-power-cooling-and-efficiency`) |
| Redundancy means maintainable | ⚠️ **Different properties. N+1 ≠ concurrently maintainable** (§17 → `hw-datacentre-facility-power-cooling-and-efficiency`) |
| Outages come from hardware failure | ⚠️ **Mostly power transfer, software and change** (§17 → `hw-datacentre-facility-power-cooling-and-efficiency`, §23 → `hw-datacentre-network-storage-failure-and-operations`) |
| Low PUE means efficient | ⚠️ **Worse IT efficiency IMPROVES PUE. It's gameable** (§19 → `hw-datacentre-facility-power-cooling-and-efficiency`) |
| Data centres should run cold | ⚠️ **ASHRAE ranges are wider than assumed; over-cooling is costly** (§18 → `hw-datacentre-facility-power-cooling-and-efficiency`) |
| Eleven nines means your data is safe | ⚠️ **Models drive failure, not operator error** (§22 → `hw-datacentre-network-storage-failure-and-operations`) |
| Failures are independent | ⚠️ **Same batch, firmware, rack, feed. They correlate** (§23 → `hw-datacentre-network-storage-failure-and-operations`) |
| GPUs are the AI constraint now | ⚠️ **Grid power and interconnection are** (§26.1) |
| Money can accelerate power delivery | ⚠️ **Transformer lead times are ~128 weeks** (§26.1) |
| 800 VDC is needed today | ⚠️ **Not until ~400 kW racks. Currently future-proofing** (§26.2) |
| Higher rack voltage is just efficiency | ⚠️ **It's copper mass and rack space — 200 kg of busbar** (§26.2) |

---
