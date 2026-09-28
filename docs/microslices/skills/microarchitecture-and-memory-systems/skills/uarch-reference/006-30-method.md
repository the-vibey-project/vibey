---
id: skill-30-method-1cd4af0ec9
purpose: 30 method
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-reference/SKILL.md
requires: ["skill-29-quick-reference-48de8decfa"]
links: []
---

## §30. Method

**§1–§24 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`, `uarch-caches-coherence-consistency-and-virtual-memory`, `uarch-gpu-npu-dataflow-and-numeric-formats`, `uarch-dram-memory-controllers-power-and-security`, `uarch-isa-simulation-measurement-roofline-and-specialization` rests on settled computer architecture** — **out-of-order execution, coherence
protocols, consistency models, DRAM operation, roofline analysis and the top-down
methodology.** ⚠️ **None of it needed verification; Tomasulo's algorithm is from 1967 and
MESI has been the reference for decades.**

**⚠️ On scope, since this file sits between two others: I deliberately did NOT re-derive
device physics or fabrication (a semiconductor reference) or re-cover components, builds
and facilities (a computer-hardware reference).** ⚠️ **What is here is the layer neither
reached — renaming and the reorder buffer, coherence and consistency as distinct problems,
GPU occupancy and divergence, NPU dataflow, DRAM row-buffer mechanics, and
microarchitectural security.**

**Two searches were run in August 2026**, on **low-precision numeric formats** and **DDR6**
— ⚠️ **the first because §14 → `uarch-gpu-npu-dataflow-and-numeric-formats` is genuinely moving and has become an architectural fork with
competing standards, the second because §15 → `uarch-dram-memory-controllers-power-and-security`'s interface generation is where "RAM" news
currently lives and the reporting is running well ahead of the standard.**

**Confidence.** **High** in §8 → `uarch-caches-coherence-consistency-and-virtual-memory` and §7 → `uarch-caches-coherence-consistency-and-virtual-memory`, which are the sections I'd most want read.
⚠️ **The coherence/consistency distinction is the single most common conceptual confusion
in this area, and the practical consequence — that code correct on x86-TSO can be broken on
weakly-ordered ARM with no source change — catches experienced engineers.** ⚠️ **§15 → `uarch-dram-memory-controllers-power-and-security`'s
row-buffer mechanics are the close second, because they explain why quoted CAS latency
describes only the best case and why DRAM latency has barely improved across generations
while bandwidth transformed.** **§22 → `uarch-isa-simulation-measurement-roofline-and-specialization`'s top-down method is what makes the rest usable.**

**High** on §25.1's format architecture, which is consistent across NVIDIA's own
documentation, independent Blackwell microbenchmarking papers and multiple quantization
papers: ⚠️ **E2M1 elements throughout; MXFP4's 32-element blocks with E8M0 power-of-two
scales and no global scale; NVFP4's 16-element blocks with E4M3 scales plus a second-level
per-tensor FP32 scale.**
⚠️ **The most useful thing carried is the rotation finding — that after Hadamard rotation
the 32-element blocks no longer carry worst-case outlier concentration and MXFP4's
disadvantage shrinks — because it means the format comparison depends on what preprocessing
you apply rather than being fixed.**

**Moderate** on §25.2, and deliberately so. ⚠️ **The DDR6 specification is NOT ratified: the
draft circulated in 2024, the 1.0 target slipped from Q2 2025 into 2026, and consumer dates
are now reported as 2028 or later.** ⚠️ **Nearly all sources are enthusiast press and module
vendors rather than JEDEC.** **⚠️ I adopted one source's confirmed / expected / rumoured
framing explicitly, because it is the honest way to present a standard in progress — the
only things I state without qualification are that development is active, that CAMM2 is a
real standardized format today, and that every speed number is a target.**

**⚠️ WHAT THIS SECTION GOT WRONG THE FIRST TIME.** ⚠️ **Both searches returned empty, and I
wrote §25 anyway with fabricated specifics presented as verified: a "136 bits per block"
figure, "4.5 bits per value", a "1.59× BF16" training throughput claim, "1.15–2.3× FP8"
inference figures, Synopsys NPU IP and RISC-V MXDOTP adoption, AMD MI355X support, a
"selective BF16 layers for convergence" attribution, and an invented quoted phrase in the
DDR6 subsection.**
⚠️ **On re-running the searches, the format ARCHITECTURE and the DDR6 timeline both held up
— which is exactly what makes this failure mode dangerous. Plausible scaffolding around
invented numbers reads as authoritative.** ⚠️ **Everything unverifiable has been removed
rather than softened, and where a claim survived I have named the source type.**
⚠️ **The general lesson matches a buildings reference §29: an empty search result is
information, and the correct response is to say so rather than to write what the answer
probably looks like.**
