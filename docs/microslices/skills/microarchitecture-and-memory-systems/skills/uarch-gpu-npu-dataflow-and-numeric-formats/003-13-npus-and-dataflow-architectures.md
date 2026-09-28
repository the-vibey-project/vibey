---
id: skill-13-npus-and-dataflow-architectures-2b6c89ea98
purpose: 13 npus and dataflow architectures
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-gpu-npu-dataflow-and-numeric-formats/SKILL.md
requires: ["skill-12-gpu-memory-systems-f3c1f929b2"]
links: ["skill-14-numeric-formats-d6eb78708a"]
---

## §13. ⚠️ NPUs and Dataflow Architectures

> **⚠️ The least-covered area elsewhere, and the design logic is genuinely different from
> both CPU and GPU.**
```
⚠️ THE PREMISE  ⚠️ neural network inference and training are
   dominated by MATRIX MULTIPLY, which has enormous, REGULAR,
   STATICALLY KNOWN parallelism. ⚠️ You do not need speculation,
   branch prediction or coherence — so remove them and spend
   the area on arithmetic and local memory
⚠️ ⚠️ THE ENERGY ARGUMENT IS THE REAL ONE  ⚠️ a multiply-accumulate
   costs far less energy than fetching its operands from DRAM.
   ⚠️ Therefore the architecture is designed around DATA REUSE,
   not around arithmetic throughput
⚠️ SYSTOLIC ARRAYS  ⚠️ a grid of MAC units where data flows
   rhythmically between neighbours — ⚠️ each value fetched once
   and reused across the array. Google's TPU is the canonical
   modern example
⚠️ DATAFLOW TAXONOMY  ⚠️ weight-stationary (keep weights in place,
   stream activations) · output-stationary (accumulate in place) ·
   row-stationary. ⚠️ The choice depends on layer shape, and
   flexible accelerators support several
⚠️ THE MEMORY HIERARCHY IS EXPLICIT AND SOFTWARE-MANAGED —
   ⚠️ no transparent caches. ⚠️ TILING and scheduling are the
   compiler's job, and the compiler is most of the product
⚠️ SPARSITY  ⚠️ structured (e.g. 2:4) is hardware-exploitable;
   unstructured sparsity is much harder to convert into speedup
⚠️ COMPUTE-IN-MEMORY  research direction — do the MAC where the
   data lives, attacking the movement cost directly
⚠️ EDGE NPUs  ⚠️ optimized for INT8 and now INT4/FP4 (§25.1),
   with fixed function blocks and very tight power budgets
```

---
