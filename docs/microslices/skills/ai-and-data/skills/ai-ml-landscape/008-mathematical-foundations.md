---
id: skill-mathematical-foundations-c6ba07b729
purpose: mathematical foundations
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-classical-ml-tabular-data-44244ce7bd"]
links: ["skill-classical-ml-reference-3f394cc82a"]
---

## Mathematical Foundations

**Linear algebra**: tensors are batched multidimensional arrays; matmul/dot products implement every linear layer and attention score; SVD underpins PCA and low-rank adaptation (LoRA literally learns low-rank ΔW). Norms drive regularization (L1 sparsity/Lasso, L2 weight decay/Ridge) and gradient clipping.

**Probability**: KL/JS/Wasserstein divergences anchor VAEs, GANs, and distribution matching. Cross-entropy is the default classification loss (= MLE under a categorical model). Bias–variance is operationalized by regularization and ensembling.

**Optimization**: backprop = reverse-mode autodiff applying chain rule over the computational graph. Deep loss landscapes are non-convex but navigable — saddle points (not bad local minima) dominate, and SGD noise helps escape them. **AdamW** is the safe default; cosine annealing with linear warmup is the standard LR schedule. First-order methods dominate because Hessian-based methods don't scale to billions of parameters.

---
