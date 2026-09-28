---
id: skill-the-transformer-attention-395a2de8eb
purpose: the transformer attention
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-deep-learning-foundations-22ae3d1ed1"]
links: ["skill-llm-training-post-training-9c06115b4d"]
---

## The Transformer & Attention

**Architecture types:**
- Encoder-only (BERT): classification/embedding
- Encoder-decoder (T5): seq2seq tasks
- Decoder-only (GPT): dominates generative LLMs

**Attention components:**
- Scaled dot-product attention over Q,K,V
- Multi-head attention
- **RoPE** (rotary positional encoding): now standard; YaRN/position interpolation extends context
- **FlashAttention (v1→v3)**: IO-aware, exact (not approximate), tiling attention in SRAM — mitigates O(n²) attention cost
- **KV cache**: makes autoregressive decoding tractable
- FFN uses **SwiGLU**

**Mixture of Experts (MoE)**: dominant frontier-scaling lever. Sparse gating + routing + load balancing. DeepSeek-V3 activates 37B of 671B params per token. Mixtral, DeepSeek-MoE, Qwen3-MoE all use this architecture.

---
