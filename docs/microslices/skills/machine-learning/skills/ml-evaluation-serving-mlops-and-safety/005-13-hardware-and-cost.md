---
id: skill-13-hardware-and-cost-8ffda29c98
purpose: 13 hardware and cost
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-evaluation-serving-mlops-and-safety/SKILL.md
requires: ["skill-12-mlops-and-reproducibility-5c07757fa1"]
links: ["skill-14-interpretability-fairness-safety-981a21c568"]
---

## §13. Hardware and Cost

**[VERSIONED]**

| Tier | Notes |
|---|---|
| **H100 (80 GB)** | ⚠️ **The software ecosystem is most mature here** — vLLM, SGLang, TensorRT-LLM, PyTorch, JAX. **Any optimization technique you read about was probably benchmarked on H100** |
| **H200 (141 GB)** | Same die as H100 with HBM3e: **141 GB and 4.8 TB/s (+43% bandwidth)**. Often better per-token cost than 2× H100 for FP16 70B |
| **Blackwell (B200/GB200/B300)** | **192 GB HBM3e** — a 70B FP16 model with real KV headroom, or 405B FP8 on two chips. NVFP4 support. ~3× faster LLM training than the prior generation by NVIDIA's own MLPerf claims |
| **Rubin / Vera** | The announced next generation, aimed at agentic training and inference |
| **RTX PRO 6000 Blackwell (96 GB)** | Workstation-class; 4–8 in a rackmount is a standard 2026 self-hosting configuration |
| **AMD MI300X / ROCm** | Real and improving; **NVIDIA remains the default for vLLM, Unsloth, and most production workflows** |
| **TPU v5e/v6, Trainium/Inferentia, Gaudi 3** | Viable, especially via JAX (TPU) or where you have committed cloud spend |

**[DURABLE] For LLM inference, memory capacity and bandwidth dominate the selection
decision, not FLOPs** (§11.2). For training, interconnect (NVLink, InfiniBand) often
matters more than per-chip performance once you're multi-node.

**Cost discipline**: cloud beats buying unless you keep hardware busy more than roughly
8 hours/day; **spot/preemptible instances plus checkpointing** are the single biggest
training cost lever; profile before scaling up (most jobs are dataloader-bound or
badly-batched, not compute-bound); and **the cheapest optimization is a smaller model that
meets the requirement.**

---
