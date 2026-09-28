---
id: skill-deep-learning-foundations-22ae3d1ed1
purpose: deep learning foundations
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-classical-ml-reference-3f394cc82a"]
links: ["skill-the-transformer-attention-395a2de8eb"]
---

## Deep Learning Foundations

### Activations & Normalization
- **ReLU**: default for CNNs
- **GELU/SiLU(Swish)**: dominate transformers (smooth, work well with normalization)
- **BatchNorm**: CNNs
- **LayerNorm/RMSNorm**: transformers (RMSNorm is cheaper, now standard in LLMs)
- **Pre-norm** (LayerNorm before sublayer): dominates modern transformers for stability at depth

### Initialization & Precision
- He/Kaiming for ReLU nets; Xavier for tanh; orthogonal for RNNs
- **BF16**: LLM-training default (wider dynamic range than FP16, no loss scaling)
- **FP8**: production on Hopper/Blackwell (DeepSeek-V3 trained in FP8)
- Mixed precision memory tools: gradient checkpointing, gradient accumulation, activation recomputation

### Residual Connections
Enable very deep networks by giving gradients an identity path.

---
