---
id: skill-27-numbers-9e32cc603a
purpose: 27 numbers
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-reference/SKILL.md
requires: ["skill-26-misconceptions-899ab93eb3"]
links: ["skill-28-books-39bfe10959"]
---

## §27. Numbers

```
⚠️ Branch frequency  ~1 in 5 instructions · ⚠️ predictors target 99%+
⚠️ Mispredict penalty  ⚠️ ~pipeline depth, order of 15-20 cycles
⚠️ Warp/wavefront  32 (NVIDIA) · 32 or 64 (AMD)
⚠️ Worst-case warp divergence  ⚠️ 32× serialization
⚠️ DRAM refresh interval  ⚠️ typically 64 ms
⚠️ Row miss cost  ⚠️ tRP + tRCD + CL ≈ 3× a row hit
⚠️ Page table levels  4-5 on x86-64 · huge pages 2 MB / 1 GB
⚠️ FP4 element  ⚠️ E2M1 — 1 sign, 2 exponent, 1 mantissa bit
⚠️ MXFP4  ⚠️ blocks of 32 · E8M0 power-of-two scale · no global scale
⚠️ NVFP4  ⚠️ blocks of 16 · E4M3 FP8 scale · + FP32 per-tensor scale
⚠️ FP4 tensor cores  ⚠️ up to 4× FP16 peak · 4-5× measured in
                     attention (SageAttention3, reported)
⚠️ DDR6 (DRAFT targets)  ⚠️ 8,800 → 17,600 MT/s · 4× 24-bit
                          sub-channels · sub-1.1 V · CAMM2
⚠️ DDR6 status  ⚠️ draft 2024 · 1.0 target Q2 2025, slipped to 2026+
⚠️ CAMM2  ⚠️ JEDEC standard since end of 2023 (Dell origin)
⚠️ DIMM T-topology penalty  ⚠️ up to 400 MT/s reported
```

---
