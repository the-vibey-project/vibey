---
id: skill-29-quick-reference-48de8decfa
purpose: 29 quick reference
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-reference/SKILL.md
requires: ["skill-28-books-39bfe10959"]
links: ["skill-30-method-1cd4af0ec9"]
---

## §29. Quick Reference

### 29.1 Picker
| Symptom | Where |
|---|---|
| Slow and I don't know why | ⚠️ **Top-down analysis first** (§22 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| Frontend bound | ⚠️ **I-cache, decode, branch mispredicts** (§2 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`, §4 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`) |
| Backend bound, memory | ⚠️ **Cache misses, DRAM, prefetch** (§6 → `uarch-caches-coherence-consistency-and-virtual-memory`, §10 → `uarch-caches-coherence-consistency-and-virtual-memory`, §15 → `uarch-dram-memory-controllers-power-and-security`) |
| Bad speculation | ⚠️ **Branch predictability, memory disambiguation** (§3 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`, §4 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`) |
| Multithreaded scaling is poor | ⚠️ **False sharing, contended atomics, NUMA** (§6 → `uarch-caches-coherence-consistency-and-virtual-memory`, §7 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Works on x86, breaks on ARM | ⚠️ **Memory ordering** (§8 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Large working set, high TLB misses | ⚠️ **Huge pages** (§9 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Pointer chasing is slow | ⚠️ **Prefetchers can't follow it. Restructure** (§10 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| GPU kernel underperforming | ⚠️ **Divergence, coalescing, occupancy — in that order** (§11 → `uarch-gpu-npu-dataflow-and-numeric-formats`) |
| Peak FLOPS not achieved | ⚠️ **You're probably bandwidth-bound** (§23 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| Should I quantize? | ⚠️ **Highest-leverage inference optimization — but not all layers** (§14 → `uarch-gpu-npu-dataflow-and-numeric-formats`, §25.1) |
| Is CL16 better than CL18? | ⚠️ **Compute ns, and only on row hits** (§15 → `uarch-dram-memory-controllers-power-and-security`) |
| Should I wait for DDR6? | ⚠️ **Not ratified. Numbers are draft targets** (§25.2) |

### 29.2 Optimization order
- [ ] ⚠️ **Measure with counters and classify top-down BEFORE changing anything** (§22 → `uarch-isa-simulation-measurement-roofline-and-specialization`)
- [ ] ⚠️ **Establish the roofline — are you compute or bandwidth bound?** (§23 → `uarch-isa-simulation-measurement-roofline-and-specialization`)
- [ ] Algorithm and complexity first (nothing here beats a better algorithm)
- [ ] ⚠️ **Reduce bytes moved: layout, blocking, fusion, quantization** (§14 → `uarch-gpu-npu-dataflow-and-numeric-formats`, §23 → `uarch-isa-simulation-measurement-roofline-and-specialization`)
- [ ] ⚠️ **Improve locality: SoA over AoS, avoid conflict strides, pad** (§6 → `uarch-caches-coherence-consistency-and-virtual-memory`, §10 → `uarch-caches-coherence-consistency-and-virtual-memory`)
- [ ] ⚠️ **Eliminate false sharing and contended atomics** (§6 → `uarch-caches-coherence-consistency-and-virtual-memory`, §7 → `uarch-caches-coherence-consistency-and-virtual-memory`)
- [ ] Consider huge pages for large working sets (§9 → `uarch-caches-coherence-consistency-and-virtual-memory`)
- [ ] Vectorize where the data layout permits (§5 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`)
- [ ] ⚠️ **On GPU: divergence, then coalescing, then occupancy** (§11 → `uarch-gpu-npu-dataflow-and-numeric-formats`)
- [ ] ⚠️ **Re-measure. Confirm the bottleneck actually moved** (§22 → `uarch-isa-simulation-measurement-roofline-and-specialization`)

---
