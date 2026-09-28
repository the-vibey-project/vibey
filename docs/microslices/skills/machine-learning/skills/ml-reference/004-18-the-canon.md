---
id: skill-18-the-canon-68b71760fe
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-4b58279b13"]
links: ["skill-19-quick-reference-aef714759f"]
---

## §18. The Canon

### 18.1 Books

| Author | Work | Why |
|---|---|---|
| **Hastie, Tibshirani, Friedman** | ***The Elements of Statistical Learning*** (**free**) | The statistical foundation. Dense and worth it |
| **James et al.** | ***An Introduction to Statistical Learning*** (**free**) | ESL's accessible sibling. **The best starting book** |
| **Goodfellow, Bengio, Courville** | ***Deep Learning*** (**free**) | The foundational DL text; dated on architectures, excellent on theory |
| **Kevin Murphy** | *Probabilistic Machine Learning* (2 vols, **free drafts**) | The most comprehensive modern reference |
| **Christopher Bishop** | *Pattern Recognition and ML*; *Deep Learning: Foundations and Concepts* (2024) | The classic, and its modern successor |
| **Aurélien Géron** | ***Hands-On ML with Scikit-Learn, Keras & TensorFlow*** | **The best practical book.** Start here if you want to build things |
| **Chip Huyen** | ***Designing Machine Learning Systems***; *AI Engineering* | **The best book on the parts that aren't modeling** — §12 → `ml-evaluation-serving-mlops-and-safety`, §1 → `ml-framing-data-and-classical`, §9 → `ml-evaluation-serving-mlops-and-safety` |
| **Andriy Burkov** | *The Hundred-Page ML Book*; *The Hundred-Page LLM Book* | Exactly what they say |
| **Jeremy Howard & Sylvain Gugger** | *Deep Learning for Coders with fastai and PyTorch* | Top-down and effective |
| **Sebastian Raschka** | *Build a Large Language Model (From Scratch)* | The clearest LLM-internals walkthrough |
| **Zhang et al.** | *Dive into Deep Learning* (**free, interactive**) | Runnable code alongside the math |
| **Pearl & Mackenzie** | *The Book of Why* | For §1.1 → `ml-framing-data-and-classical`'s prediction≠causation |

### 18.2 Papers worth reading directly
*Attention Is All You Need* (2017). *Adam* and *Decoupled Weight Decay* (AdamW) — read the
second to understand §4.2 → `ml-deep-learning-and-training`. *Batch Normalization*, *Layer Normalization*, *Deep Residual
Learning*. *Scaling Laws for Neural Language Models* (Kaplan) and *Training
Compute-Optimal LLMs* (Chinchilla). *LoRA* and *QLoRA*. *FlashAttention* 1–3. *Direct
Preference Optimization*. **"Tabular Data: Deep Learning Is Not All You Need"** and
**"Why do tree-based models still outperform deep learning on tabular data?"** for §3.1 → `ml-framing-data-and-classical`.
*Attention is not Explanation*. *Hidden Technical Debt in Machine Learning Systems*
(Sculley et al. — **read this one before you build a platform**).

### 18.3 Courses, sites, people
**Andrej Karpathy's** "Neural Networks: Zero to Hero" and **`nanoGPT`/`micrograd`** —
**the single best way to actually understand what's happening**; his *"A Recipe for
Training Neural Networks"* is the best short piece on §10 → `ml-evaluation-serving-mlops-and-safety`. **fast.ai** (top-down, practical),
**Stanford CS231n** (vision), **CS224n** (NLP), **Andrew Ng's** courses (the on-ramp),
**Hugging Face courses** (free, practical, current). **Distill.pub** (dormant but the
explanations are timeless), **The Illustrated Transformer** (Jay Alammar),
**Lil'Log** (Lilian Weng — the best technical survey blog in ML), **Sebastian Raschka's
Ahead of AI**, **Papers with Code**, and **Weights & Biases' reports**.

**People**: Karpathy, Lilian Weng, Chip Huyen, Sebastian Raschka, Jeremy Howard,
François Chollet (especially on evaluation and generalization), Yann LeCun,
Rachel Thomas (fairness), Tim Dettmers (quantization, QLoRA), Tri Dao (FlashAttention),
Horace He (PyTorch performance).

---
