---
id: skill-llm-inference-optimization-467ffd72e7
purpose: llm inference optimization
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-llm-training-post-training-9c06115b4d"]
links: ["skill-evaluation-benchmark-skepticism-4c1574b63b"]
---

## LLM Inference Optimization

### Quantization Formats
| Format | Use case | Notes |
|---|---|---|
| **AWQ** | Best throughput in vLLM; INT4 weight-only | <2% degradation on most tasks; noticeable on math/code/reasoning |
| **GPTQ** | Best throughput in vLLM | Similar trade-offs to AWQ |
| **GGUF** | llama.cpp/Ollama; CPU+GPU offload | Q4_K_M–Q6_K near-BF16 quality |
| **FP8 W8A8** | Near-lossless on Hopper/Blackwell | Production preferred when hardware supports it |

**Rule**: avoid INT4 for math/code/reasoning-critical paths.

### Serving Engines
| Engine | Strength |
|---|---|
| **vLLM** | PagedAttention; broadest model/hardware support; V1 architecture |
| **SGLang** | RadixAttention; ~29% higher H100 throughput; up to 6.4× on prefix-heavy RAG/chat |
| **TensorRT-LLM** | Maximum NVIDIA throughput |
| **Ollama/llama.cpp** | Local deployment; CPU offload |

**Continuous batching** + **disaggregated prefill/decode** (separate compute-bound prefill and bandwidth-bound decode pools) are the 2026 production patterns.

**Speculative decoding** (draft+verify, Medusa/EAGLE): 2–4× latency wins losslessly.

---
