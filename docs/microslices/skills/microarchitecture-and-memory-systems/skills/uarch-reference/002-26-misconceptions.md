---
id: skill-26-misconceptions-899ab93eb3
purpose: 26 misconceptions
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-reference/SKILL.md
requires: ["skill-25-what-s-live-checked-august-2026-37be666d65"]
links: ["skill-27-numbers-9e32cc603a"]
---

## §26. Misconceptions

| Misconception | Correction |
|---|---|
| Instructions execute in program order | ⚠️ **They execute when operands are ready; they RETIRE in order** (§3 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`) |
| Only 16 registers limits x86 | ⚠️ **Renaming maps to a much larger physical file** (§3 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`) |
| Branchless code is faster | ⚠️ **Only for UNPREDICTABLE branches** (§4 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`) |
| Cache misses are about capacity | ⚠️ **Conflict misses from stride patterns are common and fixable** (§6 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Powers-of-two array dimensions are natural | ⚠️ **They cause set conflicts. Padding can be a big win** (§6 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Atomics are slow because of the instruction | ⚠️ **Coherence traffic. Uncontended atomics are cheap** (§7 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Coherence and consistency are the same | ⚠️ **One location vs ordering across locations** (§7 → `uarch-caches-coherence-consistency-and-virtual-memory`, §8 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Correct on x86 means correct everywhere | ⚠️ **ARM is weakly ordered. Test on weak hardware** (§8 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| volatile provides synchronization | ⚠️ **It does not, in C/C++** (§8 → `uarch-caches-coherence-consistency-and-virtual-memory`) |
| Higher GPU occupancy is better | ⚠️ **Only until latency is hidden. Then it thrashes** (§11 → `uarch-gpu-npu-dataflow-and-numeric-formats`) |
| GPUs are slow at branches | ⚠️ **Only DIVERGENT ones within a warp** (§11 → `uarch-gpu-npu-dataflow-and-numeric-formats`) |
| NPUs are just small GPUs | ⚠️ **Explicit dataflow, software-managed memory, no speculation** (§13 → `uarch-gpu-npu-dataflow-and-numeric-formats`) |
| Accelerators are about FLOPS | ⚠️ **They're about data movement energy** (§13 → `uarch-gpu-npu-dataflow-and-numeric-formats`, §23 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| FP16 was replaced for precision | ⚠️ **BF16 won on RANGE, not precision** (§14 → `uarch-gpu-npu-dataflow-and-numeric-formats`) |
| CAS latency is the memory latency | ⚠️ **Only on a row hit. A miss costs ~3×** (§15 → `uarch-dram-memory-controllers-power-and-security`) |
| Faster MT/s means lower latency | ⚠️ **CL rises too. Bandwidth improved, latency barely** (§15 → `uarch-dram-memory-controllers-power-and-security`) |
| On-die ECC replaces system ECC | ⚠️ **It exists to make dense DRAM manufacturable** (§16 → `uarch-dram-memory-controllers-power-and-security`) |
| CXL memory is like local memory | ⚠️ **Meaningfully slower. It's a tier** (§17 → `uarch-dram-memory-controllers-power-and-security`) |
| Race-to-idle always wins | ⚠️ **Depends whether static or dynamic power dominates** (§18 → `uarch-dram-memory-controllers-power-and-security`) |
| Spectre was patched | ⚠️ **Meltdown largely was; Spectre exploits speculation itself** (§19 → `uarch-dram-memory-controllers-power-and-security`) |
| Old benchmarks are comparable | ⚠️ **Mitigations changed the baseline** (§19 → `uarch-dram-memory-controllers-power-and-security`, §22 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| RISC vs CISC decides performance | ⚠️ **x86 decodes to micro-ops. Decode width is the real cost** (§20 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| High IPC means good | ⚠️ **High IPC on wasted work isn't. Use top-down** (§22 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| More compute units will help | ⚠️ **Most kernels are bandwidth-bound** (§23 → `uarch-isa-simulation-measurement-roofline-and-specialization`) |
| FP4 gives 4× the throughput | ⚠️ **4× is the peak ratio; sensitive ops stay higher precision** (§14 → `uarch-gpu-npu-dataflow-and-numeric-formats`, §25.1) |
| DDR6 specs are settled | ⚠️ **Not ratified. Slipped to 2026+. Numbers are targets** (§25.2) |

---
