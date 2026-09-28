---
id: skill-14-numeric-formats-d6eb78708a
purpose: 14 numeric formats
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-gpu-npu-dataflow-and-numeric-formats/SKILL.md
requires: ["skill-13-npus-and-dataflow-architectures-2b6c89ea98"]
links: []
---

## §14. ⚠️ Numeric Formats

**⚠️ Precision is an architectural parameter now, not a given.**
```
⚠️ IEEE 754  FP64, FP32, ⚠️ FP16 (5 exponent bits — limited RANGE,
   which causes training overflow)
⚠️ BF16  ⚠️ FP32's 8 exponent bits with fewer mantissa bits —
   ⚠️ same RANGE as FP32, less precision. ⚠️ This is why BF16
   largely displaced FP16 for training: range mattered more
   than mantissa
⚠️ FP8  E4M3 (more precision) and E5M2 (more range) — typically
   used together for forward and backward passes
⚠️ INTEGER  INT8, INT4 — with quantization scale and zero-point
⚠️ ⚠️ BLOCK FLOATING POINT / MICROSCALING  ⚠️ the key modern idea:
   a group of low-precision values SHARES a higher-precision
   scale factor, recovering dynamic range at almost no bit cost
   (§25.1)
⚠️ THE TRADE  ⚠️ halving bit width roughly halves memory, memory
   BANDWIDTH and energy, and can more than double throughput —
   ⚠️ which is why quantization is the highest-leverage
   optimization available for inference
⚠️ WHAT BREAKS  ⚠️ ACTIVATION OUTLIERS — a few very large values
   force a scale that crushes everything else. ⚠️ Hence
   per-channel and per-block scaling, and Hadamard rotations
   that spread outlier energy across dimensions
⚠️ ⚠️ NOT EVERYTHING QUANTIZES  softmax, layer norm and
   accumulation are typically kept at higher precision
```

---

# PART III — MEMORY SYSTEMS
