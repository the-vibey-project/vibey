---
id: skill-5-architectures-fddc6c82c9
purpose: 5 architectures
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-deep-learning-and-training/SKILL.md
requires: ["skill-4-deep-learning-fundamentals-f25f61375d"]
links: ["skill-6-the-ecosystem-60b0974906"]
---

## §5. Architectures

### 5.1 Transformers

**[DURABLE] The dominant architecture, and worth understanding mechanically rather than by
analogy.**
```
tokens → embeddings + POSITIONAL INFORMATION
  → N × [ self-attention  →  residual+norm  →  FFN  →  residual+norm ]
    → output head

attention(Q,K,V) = softmax(QKᵀ/√d_k) V
```
Key points: **multi-head attention** runs several attention patterns in parallel;
attention is **O(n²)** in sequence length, which is the central scaling problem; the
**FFN holds most of the parameters**; and **causal masking** is what makes a decoder
autoregressive.

**The modern variants you'll meet**: **RoPE** (rotary position embeddings — now standard),
**GQA / MQA** (grouped/multi-query attention — fewer KV heads, **dramatically smaller KV
cache**, §11.2 → `ml-evaluation-serving-mlops-and-safety`), **FlashAttention** (IO-aware exact attention — not an approximation; it
avoids materializing the n² matrix in HBM), **MoE** (mixture of experts — many parameters,
few active per token), **sliding-window** and other sparse attention, and **SSMs/Mamba**
as the main non-attention contender.

### 5.2 The rest

**CNNs** — still the right choice for many vision tasks, especially with limited data and
compute; ConvNeXt showed a modernized CNN matches ViTs. Convolution's inductive bias
(locality, translation equivariance) is a *feature* when data is scarce.
**Vision Transformers** — win at scale, need more data or heavy augmentation.
**Diffusion models** — the generative image/video/audio default; iterative denoising, with
flow matching as the cleaner modern formulation.
**GNNs** — for genuinely graph-structured data. ⚠️ Often beaten by feature engineering plus
a GBDT; verify the graph structure actually carries signal.
**Encoder-decoder vs. decoder-only** — decoder-only won for general LLMs; encoder models
(BERT-family) remain excellent and much cheaper for classification and retrieval, and are
badly underused because attention moved elsewhere.
**Embedding models** — the workhorse of retrieval, RAG, semantic search, and dedup, and
often the highest-value-per-FLOP thing you can deploy.

---
