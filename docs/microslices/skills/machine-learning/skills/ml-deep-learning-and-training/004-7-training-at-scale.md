---
id: skill-7-training-at-scale-9b995b1d59
purpose: 7 training at scale
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-deep-learning-and-training/SKILL.md
requires: ["skill-6-the-ecosystem-60b0974906"]
links: ["skill-8-fine-tuning-and-adaptation-fc6de13deb"]
---

## §7. Training at Scale

### 7.1 The parallelism taxonomy

| Strategy | Splits | Use when |
|---|---|---|
| **Data parallel (DDP)** | The batch | **The default.** Model fits on one GPU |
| **FSDP / ZeRO** | Parameters, gradients, optimizer state | Model doesn't fit. **The mainstream large-model answer** |
| **Tensor parallel** | Individual matrices, within a layer | Very large layers; needs fast interconnect (NVLink) |
| **Pipeline parallel** | Layers across devices | Very deep models; ⚠️ introduces bubbles |
| **Expert parallel** | MoE experts | MoE models |
| **Context/sequence parallel** | The sequence dimension | Very long context |

**[DURABLE] Real large-scale training composes several of these** ("3D parallelism" and
beyond), and the composition is chosen against your interconnect topology, not in the
abstract. **Communication is usually the bottleneck**, which is why NVLink/InfiniBand
topology drives the design.

**[VERSIONED]** PyTorch's **FSDP2** now supports overlapping reduce-scatter and all-gather
via separate process groups (opt-in), which increases throughput; and **torchcomms** is a
new communications backend for PyTorch Distributed aimed at fault tolerance, scalability,
and debuggability on large clusters — with plans to make it the default, including
breaking changes to how ProcessGroups operate (eager initialization, single backend
device). **If you run large distributed jobs, that migration is on your horizon.**

### 7.2 Mixed precision

**[DURABLE]** Train in low precision, keep a master copy and accumulations in higher
precision.
- **FP16** — needs **loss scaling** (gradients underflow otherwise).
- **BF16** — same exponent range as FP32, less mantissa. **No loss scaling needed. The
  default on modern hardware, and the right choice.**
- **FP8** — real on Hopper and Blackwell; needs careful scaling; increasingly used in
  production training.
- **[VERSIONED] NVFP4 / MXFP4** — 4-bit formats with hardware support on Blackwell,
  now appearing in both training and inference paths.

### 7.3 Memory

**[DURABLE] Know where the memory goes**, because "CUDA out of memory" is the most common
obstacle in practice:
```
parameters  +  gradients  +  OPTIMIZER STATE  +  activations  +  fragmentation
                                    ↑
              Adam keeps 2 extra copies — often the largest single term
```
A rough anchor: **fp32 Adam training costs roughly 16 bytes per parameter** (4 param +
4 grad + 8 optimizer state), before activations. That's why a 7B model doesn't fit on an
80 GB card without help.

**The levers**: **gradient checkpointing** (recompute activations — trades ~30% compute for
large memory savings), **gradient accumulation**, **8-bit or fused optimizers**, **FSDP
sharding**, **`nn.LinearCrossEntropyLoss`** (a 2026 PyTorch addition fusing the final
projection and loss — **cuts peak memory by up to 4× for large-vocabulary LM training**,
where the logits tensor is genuinely enormous), and simply **reducing sequence length**.

---
