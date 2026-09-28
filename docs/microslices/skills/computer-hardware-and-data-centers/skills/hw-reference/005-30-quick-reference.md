---
id: skill-30-quick-reference-7334165f39
purpose: 30 quick reference
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-reference/SKILL.md
requires: ["skill-29-sources-caeee3115c"]
links: ["skill-31-method-1d177372ef"]
---

## §30. Quick Reference

### 30.1 Picker
| Question | Where |
|---|---|
| What should I upgrade? | ⚠️ **Measure first. Find the actual bottleneck** (§1 → `hw-bottlenecks-cpu-memory-gpu-and-storage`, §15 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| Why is my code slow? | ⚠️ **Suspect memory access patterns** (§3 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| How much RAM do I need? | ⚠️ **Enough. Beyond that, capacity beats speed** (§3 → `hw-bottlenecks-cpu-memory-gpu-and-storage`) |
| How big a PSU? | ⚠️ **Not double. Check transient handling** (§7 → `hw-interconnect-power-thermals-and-networking`) |
| Is my system throttling? | ⚠️ **Monitor under sustained load** (§8 → `hw-interconnect-power-thermals-and-networking`, §14 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| Random crashes | ⚠️ **PSU transients, RAM (test overnight), XMP** (§14 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| Build won't POST | ⚠️ **CPU 8-pin, reseat RAM, debug LEDs** (§14 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| Is this benchmark trustworthy? | ⚠️ **Check lows, duration, config, repeats** (§15 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`) |
| How do I size a facility? | ⚠️ **Power first — it runs out first** (§17 → `hw-datacentre-facility-power-cooling-and-efficiency`, §24 → `hw-datacentre-network-storage-failure-and-operations`, §26.1) |
| Is a low PUE good? | ⚠️ **Only alongside work per watt** (§19 → `hw-datacentre-facility-power-cooling-and-efficiency`) |
| Can this rack take an AI node? | ⚠️ **Power AND cooling AND floor loading** (§20 → `hw-datacentre-facility-power-cooling-and-efficiency`, §26.2) |
| Why did the data centre go down? | ⚠️ **Statistically: power transfer, or a change** (§17 → `hw-datacentre-facility-power-cooling-and-efficiency`, §23 → `hw-datacentre-network-storage-failure-and-operations`) |
| Why can't we just build more? | ⚠️ **Interconnection queue and transformers** (§26.1) |

### 30.2 Build and deployment checks
- [ ] ⚠️ **Workload identified and the likely bottleneck named** (§1 → `hw-bottlenecks-cpu-memory-gpu-and-storage`, §10 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`)
- [ ] ⚠️ **Components balanced — no starved GPU, no starved CPU** (§10 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`)
- [ ] ⚠️ **PSU sized on transients, not just continuous rating** (§7 → `hw-interconnect-power-thermals-and-networking`)
- [ ] ⚠️ **RAM in correct slots; XMP/EXPO enabled and verified** (§11 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`, §12 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`)
- [ ] Every power connector fully seated (§7 → `hw-interconnect-power-thermals-and-networking`, §11 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`)
- [ ] ⚠️ **Sustained-load thermal test, not just idle** (§8 → `hw-interconnect-power-thermals-and-networking`, §14 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`)
- [ ] Memory tested overnight before trusting the system (§14 → `hw-specifying-assembly-firmware-tuning-and-benchmarking`)
- [ ] ⚠️ **Backups exist and a restore has been TESTED** (§5 → `hw-bottlenecks-cpu-memory-gpu-and-storage`)
- [ ] **At facility scale, additionally:**
- [ ] ⚠️ **Power availability confirmed with a real timeline** (§26.1)
- [ ] ⚠️ **Cooling capacity matched to rack density, with liquid path planned** (§18 → `hw-datacentre-facility-power-cooling-and-efficiency`, §26.2)
- [ ] ⚠️ **Redundancy AND concurrent maintainability distinguished** (§17 → `hw-datacentre-facility-power-cooling-and-efficiency`)
- [ ] ⚠️ **Generator and battery testing scheduled and actually done** (§17 → `hw-datacentre-facility-power-cooling-and-efficiency`)
- [ ] ⚠️ **Fault domains and correlated-failure assumptions examined** (§23 → `hw-datacentre-network-storage-failure-and-operations`)
- [ ] ⚠️ **Change management treated as a reliability control** (§23 → `hw-datacentre-network-storage-failure-and-operations`)

---
