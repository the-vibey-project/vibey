---
id: skill-25-what-s-live-checked-august-2026-37be666d65
purpose: 25 what s live checked august 2026
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-reference/SKILL.md
requires: []
links: ["skill-26-misconceptions-899ab93eb3"]
---

## §25. What's Live — checked August 2026

> **⚠️ CORRECTION NOTICE.** ⚠️ **This section was first drafted when both searches returned
> EMPTY results, and I wrote it anyway — inventing specific bit-counts, throughput
> multipliers, vendor adoption claims and a quoted phrase, and presenting them as verified.
> That is the same failure mode documented in a buildings reference §29.**
> ⚠️ **The searches were re-run and this section rebuilt. The format architecture survived
> verification; several specific numbers did not and have been removed. §30 records what
> changed.**

### 25.1 ⚠️ Low-precision formats: block scaling won, and there are two competing standards
**⚠️ §14 → `uarch-gpu-npu-dataflow-and-numeric-formats`'s subject moving fast, and it is now a genuine architectural fork.**

- **⚠️ THE IDEA THAT WON.** ⚠️ **Raw FP4 has a very limited representable range, so values
  must be quantized WITH SCALING.** ⚠️ **Microscaling formats solve this by having a block
  of low-precision elements share a common scale factor — trading per-element independence
  for compression.**
- **⚠️ THE TWO FORMATS, and the difference is precise.** ⚠️ **Both use E2M1 elements — 1
  sign, 2 exponent, 1 mantissa bit — and differ in exactly two places:**
  ⚠️ **MXFP4 (the open OCP standard, Rouhani et al. 2023) uses blocks of 32 with an E8M0
  exponent-only, power-of-two scale, and no global scale — the larger block amortizes scale
  overhead and E8M0 gives wide dynamic range for coarse adjustment.**
  ⚠️ **NVFP4 (NVIDIA, introduced June 2025) uses blocks of 16 with a full FP8 E4M3 scale,
  PLUS a second-level per-tensor FP32 scale.** ⚠️ **The two-level design is deliberate: the
  tensor-level FP32 scale remaps the distribution into a range compatible with block
  scaling, then the block-level E4M3 scale maps each block into FP4 range.**
- **⚠️ WHY THE SMALLER BLOCK.** ⚠️ **NVIDIA's own explanation is §14 → `uarch-gpu-npu-dataflow-and-numeric-formats`'s outlier problem
  directly: large tensors mix large and small numbers, and a single "umbrella" scale causes
  significant quantization errors.** ⚠️ **Halving the group from 32 to 16 gives twice as
  many opportunities to match the local dynamic range.**
- **⚠️ THE TRADE IS EXPLICIT.** ⚠️ **Academic sources describe NVFP4's finer scaling as
  coming "at the cost of a slightly higher bit budget per element" — a trade-off between
  representational accuracy and compression efficiency.**
- **⚠️ IT IS SHIPPING.** ⚠️ **Blackwell's fifth-generation Tensor Cores implement both, with
  hardware handling element grouping, dynamic scaling and 4-bit matrix operations
  automatically, plus dequantization logic converting FP4 to higher precision (typically
  FP8 or FP16) during the multiply.** ⚠️ **Accumulation is in FP32.** ⚠️ **Native FP4
  training is reported in some leading open models as of mid-2026.**

> **⚠️ GOTCHA — FP4 does not simply work, and the supporting algorithmic machinery is where
> the real research effort sits.** ⚠️ **Reported problems and responses:**
> ⚠️ **WEIGHT OSCILLATION in the forward pass is identified as the main source of MXFP4
> training degradation, addressed by EMA quantizers and adaptive ramping.**
> ⚠️ **INTER-BLOCK VARIANCE IMBALANCE — a minority of high-variance blocks force the shared
> scale upward and coarsen small-magnitude activations within the block.**
> ⚠️ **HADAMARD / orthogonal ROTATIONS spread outlier energy across dimensions; one source
> notes that after rotation, 32-element blocks no longer carry worst-case outlier
> concentration and MXFP4's E8M0 disadvantage SHRINKS — so the format gap is partly an
> artefact of what preprocessing you apply.**
> ⚠️ **MIXED PRECISION within a model is standard practice, with per-layer format selection
> across MXFP4/MXFP6/MXFP8.**

**⚠️ On speedups, only what is actually sourced**: ⚠️ **Blackwell's FP4 Tensor Cores are
described as offering up to 4× over FP16 in principle, and a reported 4–5× speedup over
FP16 has been measured in attention specifically (SageAttention3).** ⚠️ **Treat end-to-end
model speedups as substantially lower than the peak ratio, because sensitive operations
stay at higher precision** (§14 → `uarch-gpu-npu-dataflow-and-numeric-formats`).
**⚠️ Sourcing note: the format specifications are consistent across NVIDIA's documentation,
independent microbenchmarking papers and multiple quantization papers, so I hold them with
high confidence.** ⚠️ **Vendor-published accuracy claims are not reproduced here, because I
could not verify the specific figures I had originally written.**

### 25.2 ⚠️ DDR6 and the module format change
**⚠️ §15 → `uarch-dram-memory-controllers-power-and-security`'s interface generation — and a case where reporting runs well ahead of the
standard.**

- **⚠️ WHERE IT ACTUALLY IS.** ⚠️ **JEDEC circulated the initial DDR6 draft in 2024;
  ratification of Specification 1.0 was targeted for Q2 2025 and has SLIPPED INTO 2026 as
  JEDEC refines timing and signaling parameters.** ⚠️ **LPDDR6 — a separate standard on its
  own timeline — was published in July 2025.**
- **⚠️ REPORTED TARGETS, and they are targets.** ⚠️ **Base rate around 8,800 MT/s scaling
  toward 17,600 MT/s within the standard, with overclocked kits pushing higher.**
  ⚠️ **Architecturally, DDR6 replaces DDR5's two 32-bit sub-channels with FOUR 24-bit
  sub-channels — more parallelism, and correspondingly harder signal integrity — plus lower
  voltage than DDR5's 1.1 V and DVFS.**
- **⚠️ THE MODULE CHANGE IS THE INTERESTING PART, and the reason is electrical.**
  ⚠️ **CAMM2 (Compression Attached Memory Module) mounts FLAT and parallel to the board
  using a land grid array and compression plate.** ⚠️ **It originated at Dell and became a
  JEDEC standard at the end of 2023.** ⚠️ **The motivation: DIMM slot T-topology causes
  signaling problems at high DDR5 speeds — one report attributes up to 400 MT/s of lost
  headroom to interference from DIMM slot soldered connections — and CAMM2 moves the
  topology onto the module where the signal path can be tuned.**
- **⚠️ TIMELINE, honestly.** ⚠️ **As of mid-2026: prototype DDR6 chips exist; Samsung, SK
  hynix and Micron are in validation with substrate manufacturers; platform-level
  validation with Intel and AMD is underway; the JEDEC spec is still being finalized.**
  ⚠️ **Enterprise and data centre DDR6 is expected around 2027, with consumer desktop
  reported variously as 2028 or later.**

> **⚠️ GOTCHA — one source states the epistemics unusually well, and it is worth adopting
> wholesale.** ⚠️ **CONFIRMED: DDR6 is in active development at JEDEC; Samsung, SK hynix and
> Micron have shown prototype work; CAMM2 exists as a real standardized module format
> today.** ⚠️ **EXPECTED / ON THE ROADMAP: the specific speed tiers, the channel redesign,
> and DDR6 adopting CAMM2 for desktops — "widely reported targets, and they may shift before
> the spec is locked."** ⚠️ **RUMOURED / UNSCHEDULED: exact consumer launch dates, pricing,
> and which CPU generations will support it.**
> ⚠️ **Another source puts the same warning plainly: many circulating DDR6 specifications
> are industry targets or preliminary information rather than final JEDEC requirements, and
> speed, voltage, module layout and platform compatibility can all change.**
> **⚠️ And the point that matters most for anyone planning around it: raw transfer rates
> should never be read as equivalent to real-world application performance** (§15 → `uarch-dram-memory-controllers-power-and-security`'s finding
> that latency has barely improved across generations while bandwidth transformed).

**⚠️ The practical consequence if CAMM2 displaces DIMMs**: ⚠️ **the module is a single unit,
so incremental "add another stick" upgrades stop being possible.** ⚠️ **There is genuine
scepticism too — CAMM2 and LPCAMM2 were designed for thin-and-light notebook z-height
constraints rather than desktops, one report notes CAMM2 likely won't be used directly in
servers, and enthusiast commentary questions how it would work on smaller board formats.**
⚠️ **Note also that DIMMs have not stopped improving — CUDIMMs are reported reaching around
10,000 MT/s, which weakens the "DIMMs have hit the wall" framing somewhat.**
**⚠️ Sourcing caution: this section draws almost entirely on enthusiast tech press, module
vendors and aggregator sites rather than JEDEC directly.** ⚠️ **I have seen no announcement
of a final ratified DDR6 specification, and dates have already slipped repeatedly.**

---
