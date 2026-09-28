---
id: skill-17-currency-snapshot-verified-august-2026-4b58279b13
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-reference/SKILL.md
requires: ["skill-16-contested-questions-ade82d56c5"]
links: ["skill-18-the-canon-68b71760fe"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **PyTorch** | **2.13 (July 2026)** — 3,328 commits from 526 contributors since 2.12. **FlexAttention on Apple Silicon (MPS)** with ~12× speedup over SDPA on sparse patterns, plus a deterministic CUDA backward path. **CuTeDSL "Native DSL" Inductor backend** alongside Triton for GEMM/RMSNorm. **`nn.LinearCrossEntropyLoss`** cuts peak GPU memory **up to 4×** for large-vocab LM training. **torchcomms** distributed backend. **FSDP2 reduce-scatter/all-gather overlap** (opt-in). Python 3.15 wheels incl. free-threaded 3.15t. ⚠️ **Breaking: named tensors and Bazel build removed** | **High** |
| **PyTorch release cadence** | Roughly quarterly: 2.9 (Oct 2025), 2.10 (Jan 2026), 2.11 (Mar 2026), 2.12 (May 2026), 2.13 (Jul 2026) | **High** |
| **torchcomms migration** | ⚠️ PyTorch plans to make **torchcomms the default in 2.13+**, with **breaking ProcessGroup changes** — eager initialization required at `dist.init_process_group`, single backend device only. Available now via `pip install torchcomms` + `TORCH_DISTRIBUTED_USE_TORCHCOMMS=1` | **High** |
| **Python support** | ⚠️ **CPython 3.13t (free-threaded) binaries dropped** — manylinux removed 3.13t on **7 May 2026** as superseded by non-experimental 3.14t. Move free-threaded workloads to 3.14t | Medium |
| **TGI** | ⚠️ **Maintenance mode** — announced December 2025, **repository archived read-only 21 March 2026**, redirecting to vLLM, SGLang, llama.cpp, MLX | Low |
| **Serving engines** | **vLLM** is the practical default (NVIDIA CUDA, AMD ROCm, Intel XPU, Google TPU, Trainium/Inferentia, Gaudi, Arm). **SGLang** for prefix-heavy workloads (RadixAttention) — one comparison reports ~29% higher throughput than vLLM on H100 and much larger gains on RAG/multi-turn. **TensorRT-LLM** for deepest NVIDIA optimization. **FlashInfer** is the default attention backend for vLLM on Blackwell and for SGLang on both Hopper and Blackwell | Medium |
| **NVIDIA Dynamo** | Inference layer disaggregating prefill and decode; NVIDIA claims **up to 7× throughput per GPU** for DeepSeek R1 on GB200 NVL72. Integrates with TensorRT-LLM, vLLM, SGLang | Medium |
| **Hardware** | **H100 80GB** — most mature software ecosystem. **H200** — 141 GB, 4.8 TB/s (+43% bandwidth). **Blackwell B200/GB200/B300** — 192 GB HBM3e, NVFP4; NVIDIA claims ~3× faster LLM training than prior gen. **Rubin/Vera** announced for agentic training and inference. **RTX PRO 6000 Blackwell (96 GB)** for workstation-class serving | Medium |
| **Inference economics** | **Inference is now ~2/3 of all AI compute** (up from ~1/3 in 2023). Cost-per-token: **~$0.40/M tokens for GPT-4-equivalent in early 2026 vs ~$20 in late 2022**. Engine improvements took GPU utilization from **~30–40% to ~70–80%**. Self-hosting reaches API cost parity within **1–4 months at ~30M tokens/day** in one 2026 study | Medium |
| **Gradient boosting** | **XGBoost 3.2** (mature categoricals, terabyte-scale external memory), **LightGBM 4.6** (fastest, lowest memory), **CatBoost 1.2.10** (best defaults on categorical-heavy data). ⚠️ **The gap between them has narrowed to near-irrelevance** — feature engineering and tuning matter more. **HistGradientBoosting** identified as most stable across datasets in comparative work | Low |
| **Tabular DL vs GBDT** | Trees still lead on the weight of benchmark evidence (Shwartz-Ziv & Armon; Grinsztajn et al.), though newer benchmarks (TabArena, OmniTabBench) and foundation models like **TabPFN** — strong on *small* datasets — keep the question live | Medium |

**Goes stale fastest:** PyTorch versions and APIs; serving-engine benchmarks; GPU
generations and pricing; inference cost figures. **Essentially never stale:** §1 → `ml-framing-data-and-classical` (framing),
§2 → `ml-framing-data-and-classical` (leakage), §4 → `ml-deep-learning-and-training` (optimization fundamentals), §9 → `ml-evaluation-serving-mlops-and-safety` (evaluation discipline), §10 → `ml-evaluation-serving-mlops-and-safety` (debugging
ladder), §14.2 → `ml-evaluation-serving-mlops-and-safety` (fairness impossibility), §15 (anti-patterns).

---
