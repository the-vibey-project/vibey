---
id: skill-16-memory-controllers-f61118b65c
purpose: 16 memory controllers
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-dram-memory-controllers-power-and-security/SKILL.md
requires: ["skill-15-dram-internals-509a82c954"]
links: ["skill-17-emerging-memory-interfaces-a711ebe857"]
---

## §16. Memory Controllers

**⚠️ The controller is a scheduler**, ⚠️ **and its policies matter as much as the DRAM
timings.**
⚠️ **SCHEDULING: FR-FCFS (first-ready, first-come-first-served) prioritizes ROW HITS over
program order, which raises throughput and can starve latency-sensitive threads.**
**⚠️ Address mapping** determines how physical addresses distribute across channels, ranks,
banks and rows — ⚠️ **and a bad mapping for a given access pattern destroys bank
parallelism.**
**⚠️ Open-page versus closed-page policy** trades row-hit rate against precharge latency
for random access.
**⚠️ Refresh management, power-down states, and write-to-read turnaround** — ⚠️ **bus
turnaround is a real cost, so controllers batch reads and writes.**
**⚠️ ECC**: ⚠️ **SECDED at the module level; ⚠️ ON-DIE ECC in DDR5 exists to make the DRAM
manufacturable at density and does NOT replace system ECC — a distinction vendors blur.**

---
