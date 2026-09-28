---
id: skill-11-inference-and-serving-9ddb9438ae
purpose: 11 inference and serving
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-evaluation-serving-mlops-and-safety/SKILL.md
requires: ["skill-10-debugging-training-ecd081429a"]
links: ["skill-12-mlops-and-reproducibility-5c07757fa1"]
---

## §11. Inference and Serving

### 11.1 The landscape

**[VERSIONED — this layer moved fast and consolidated in 2025–2026.]**

| Engine | Best for |
|---|---|
| **vLLM** | **The practical default.** Broadest hardware support (NVIDIA CUDA, AMD ROCm, Intel XPU, Google TPU, and more), one `pip` install, OpenAI-compatible server immediately |
| **SGLang** | **Long shared prefixes** — RAG over a fixed corpus, multi-turn agents, structured decoding. **RadixAttention** turns prefix overlap into automatic cache hits. Reported ~29% higher throughput than vLLM on H100 in one comparison, with much larger gains on prefix-heavy workloads |
| **TensorRT-LLM** | Committed to NVIDIA's newest silicon and want the deepest kernel-level optimization — **paid for in build complexity** |
| **llama.cpp / Ollama / MLX** | Single-user local inference, CPU and Apple Silicon |
| **Triton Inference Server / Ray Serve** | General model serving, multi-model, non-LLM |

**⚠️ [VERSIONED] Hugging Face TGI moved to maintenance mode** (announced December 2025,
repository archived read-only **21 March 2026**), redirecting users to vLLM, SGLang,
llama.cpp, and MLX. **If you're on TGI, plan a migration.**

**[DURABLE] The feature set has converged.** Any modern engine gives you **continuous
(in-flight) batching** — new requests join the running batch the moment a slot frees, which
is the single biggest throughput unlock over naïve batching — and a **paged KV cache**
(virtual-memory management for the attention K/V store). Choose on hardware breadth,
workload shape, and operational complexity, not on feature checklists.

### 11.2 What actually determines inference cost

**[DURABLE]** LLM inference has two distinct phases with completely different bottlenecks:
- **Prefill** (processing the prompt) — **compute-bound**, parallel across tokens.
- **Decode** (generating tokens) — **memory-bandwidth-bound**, one token at a time.

**This asymmetry drives everything**: it's why **disaggregated prefill/decode** (routing
each phase to different hardware) is a major 2026 architecture, why **memory bandwidth
matters more than FLOPs** for serving, and why batch size helps decode enormously.

**The KV cache is usually your real memory constraint**, growing linearly with batch size
and sequence length. **GQA/MQA**, **paged attention**, **prefix caching**, and **KV cache
quantization** all exist to attack it.

**Other levers**: **quantization** (§11.3), **speculative decoding** (a small draft model
proposes, the big model verifies — real latency wins), **prefix caching**, and **structured
output constraints**.

### 11.3 Quantization

| Format | Use |
|---|---|
| **INT8 / W8A8** | Well-established, minimal quality loss |
| **INT4 / W4A16** (GPTQ, AWQ) | **The common serving choice.** ~4× memory reduction, small quality cost |
| **FP8** | Native hardware support on Hopper/Blackwell; good quality retention |
| **NVFP4 / MXFP4** | 4-bit with Blackwell hardware support; increasingly used |
| **GGUF (k-quants)** | The llama.cpp ecosystem, CPU and Apple Silicon |

**[DURABLE] Quantization-aware training beats post-training quantization on quality and
costs more.** For most people PTQ with a good calibration set is sufficient. **⚠️ Always
evaluate the quantized model on your own task** — published "negligible degradation" claims
are measured on benchmarks that may have nothing to do with your use case, and degradation
is often concentrated in exactly the hard cases you care about.

### 11.4 The economics

**[VERSIONED, and the trend is the point]**: **inference now accounts for roughly two-thirds
of all AI compute, up from about one-third in 2023**, and cost-per-token has fallen by
orders of magnitude — one analysis puts GPT-4-equivalent performance at roughly **$0.40 per
million tokens in early 2026 versus ~$20 in late 2022**. Serving-engine improvements are a
large part of it: **GPU utilization went from ~30–40% to ~70–80%** through continuous
batching, paged attention, and speculative decoding.

**[DURABLE] The practical consequence: cost-per-token is the KPI**, and a 10× inference cost
reduction directly enables 10× the users at the same budget. Self-hosting reaches cost
parity with commercial APIs at moderate volume — one 2026 study found parity within 1–4
months at ~30M tokens/day — but **only if you actually keep the hardware busy.**

---
