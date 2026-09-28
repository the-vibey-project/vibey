---
id: skill-18-power-and-clocking-48545d57bd
purpose: 18 power and clocking
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-dram-memory-controllers-power-and-security/SKILL.md
requires: ["skill-17-emerging-memory-interfaces-a711ebe857"]
links: ["skill-19-microarchitectural-security-620ea5ed6b"]
---

## §18. Power and Clocking

**⚠️ Dynamic power ∝ C·V²·f, and the V² term is why voltage scaling was so powerful and its
end so consequential** (see a semiconductor reference §5).
**⚠️ Static/leakage power** now matters at idle and scales badly.
**⚠️ DVFS** — ⚠️ **and because power scales with V² while frequency scales roughly with V,
running slower saves power SUPERLINEARLY.**
**⚠️ Race-to-idle versus run-slow** is genuinely workload-dependent: ⚠️ **when static power
and fixed overheads dominate, finishing fast and sleeping deeply wins; when dynamic power
dominates, running slow wins.**
**⚠️ Clock and power gating; multiple voltage and clock domains; and thermal/current
throttling as the real limiter** (see a computer-hardware reference §8).
**⚠️ Energy per operation is the metric that matters** for accelerators (§13 → `uarch-gpu-npu-dataflow-and-numeric-formats`), ⚠️ **not
peak throughput.**

---
