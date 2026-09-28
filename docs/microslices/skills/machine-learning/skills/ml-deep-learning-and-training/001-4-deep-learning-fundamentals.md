---
id: skill-4-deep-learning-fundamentals-f25f61375d
purpose: 4 deep learning fundamentals
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-deep-learning-and-training/SKILL.md
requires: []
links: ["skill-5-architectures-fddc6c82c9"]
---

## §4. Deep Learning Fundamentals

### 4.1 The machinery

```
forward pass  →  loss  →  BACKPROP (reverse-mode autodiff)  →  optimizer step
                              ↑
                    the chain rule, applied over a computation graph
```
**[DURABLE] Backpropagation is reverse-mode automatic differentiation**, not a separate
algorithm. Understanding it as autodiff over a graph explains why memory scales with
activations (you must keep intermediates for the backward pass), why gradient checkpointing
works (recompute instead of store), and why `detach()`/`stop_gradient` does what it does.

### 4.2 Optimization

| Optimizer | Notes |
|---|---|
| **SGD + momentum** | Still competitive for vision; often generalizes better than adaptive methods |
| **Adam / AdamW** | **The default.** ⚠️ **Use AdamW, not Adam, whenever you use weight decay** — Adam's L2 penalty is not equivalent to weight decay, and this measurably hurts |
| **Adafactor / 8-bit Adam** | Memory-efficient for large models — optimizer state is often the largest memory consumer (§7.3) |
| **Muon, Shampoo, second-order** | Active area; real wins reported at scale, less settled than the marketing |

**Learning rate is the hyperparameter that matters most, by a wide margin.** Practices that
consistently pay: **warmup** (especially with transformers and large batches), **cosine or
linear decay**, and an **LR-range test** to find the scale. **[DURABLE] If you can tune only
one thing, tune the learning rate.**

**Batch size** interacts with LR (linear scaling rule as a starting heuristic), affects
generalization, and is often set by memory rather than by choice. **Gradient accumulation**
simulates a large batch on small hardware.

### 4.3 The things that make training work

- **Initialization** — Xavier/Glorot for tanh-family, **He/Kaiming for ReLU-family**.
  Getting this wrong causes vanishing or exploding activations before you write a single
  training loop.
- **Normalization** — **BatchNorm** (⚠️ batch-size dependent, and it behaves differently in
  train vs. eval — a classic bug source), **LayerNorm** (the transformer standard),
  **RMSNorm** (cheaper, now widely preferred in LLMs), GroupNorm.
- **Residual connections** — the innovation that made deep networks trainable at all.
- **Activations** — ReLU, GELU, **SiLU/Swish**, and **SwiGLU** (the modern LLM FFN default).
- **Regularization** — weight decay, dropout (⚠️ largely fallen out of favour in large
  transformers), early stopping, data augmentation (**the most effective regularizer in
  vision**), label smoothing, and mixup/cutmix.
- **Gradient clipping** — by global norm. Cheap insurance against loss spikes.

### 4.4 The bias-variance picture, updated

**[DURABLE, but the classical story is incomplete.]** The textbook U-curve — underfit,
sweet spot, overfit — is real for classical models. **Double descent** complicates it:
past the interpolation threshold, test error can *decrease again* as you keep adding
capacity, which is part of why enormously overparameterized networks work at all.
**Practical implication: "the model is too big, it will overfit" is not a reliable
argument for deep networks**, and regularization plus data scale matters more than
parameter count.

---
