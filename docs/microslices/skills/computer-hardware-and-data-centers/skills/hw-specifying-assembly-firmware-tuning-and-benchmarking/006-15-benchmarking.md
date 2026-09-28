---
id: skill-15-benchmarking-89834430a7
purpose: 15 benchmarking
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-specifying-assembly-firmware-tuning-and-benchmarking/SKILL.md
requires: ["skill-14-troubleshooting-ad1ed73cf4"]
links: []
---

## §15. ⚠️ Benchmarking

> **⚠️ Most published comparisons are misleading, and the errors are systematic rather than
> random.**
**⚠️ Synthetic vs real workload**: ⚠️ **synthetics are repeatable and frequently don't
predict your application; run YOUR workload if you can.**
**⚠️ The methodology errors that matter**: ⚠️ **testing only average FPS while ignoring
1% and 0.1% LOWS (⚠️ which is what actually feels bad); short runs that miss thermal
steady state; run-to-run variance reported without repeats; comparing across different
driver, firmware and OS versions; and ⚠️ CPU tests run at resolutions where the GPU is the
limit, which flattens all CPUs into a meaningless tie.**
**⚠️ Vendor benchmarks** are selected, not falsified — ⚠️ **and the selection is the whole
effect.**
**⚠️ For servers**: ⚠️ **measure TAIL latency (p99, p99.9) rather than mean, because mean
latency hides exactly the behaviour users notice.**
**⚠️ The discipline**: ⚠️ **state the configuration completely, repeat, report variance,
and change one variable at a time** (§14).

---

# PART III — DATA CENTRES
