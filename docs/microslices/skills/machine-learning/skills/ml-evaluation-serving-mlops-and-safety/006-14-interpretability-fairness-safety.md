---
id: skill-14-interpretability-fairness-safety-981a21c568
purpose: 14 interpretability fairness safety
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-evaluation-serving-mlops-and-safety/SKILL.md
requires: ["skill-13-hardware-and-cost-8ffda29c98"]
links: []
---

## §14. Interpretability, Fairness, Safety

### 14.1 Interpretability

**Intrinsically interpretable models** — linear models, small trees, GAMs — are
underrated. **[DURABLE] If interpretability is a hard requirement, use an interpretable
model rather than explaining a black box.**

**Post-hoc methods**: **SHAP** (game-theoretic, the practical standard; ⚠️ correlated
features make attributions ambiguous), **LIME** (local surrogates; unstable),
**permutation importance** (⚠️ misleading with correlated features), **partial dependence
and ICE**, attention maps (⚠️ **attention is not explanation** — a well-known result;
attention weights don't reliably indicate what drove the output), and **counterfactuals**
(often the most *useful* form for an affected person).

**⚠️ Feature importance is not causal.** A high-importance feature tells you what the model
uses, not what drives the outcome. Acting on it as if it were causal is a recurring and
expensive error.

### 14.2 Fairness

**[DURABLE] The mathematics constrains you**: demographic parity, equalized odds, and
calibration within groups are **provably mutually incompatible** except in degenerate cases.
**You must choose which fairness definition applies to your context** — there is no
technically neutral option, and pretending otherwise is itself a choice.

Practically: **slice every metric by group** (§9.2 — this is the same practice as good
evaluation), audit training data for representation and historical bias, remember that
**removing a protected attribute doesn't remove its influence** (proxies are everywhere),
and document the model's intended use and limitations (model cards, datasheets).

### 14.3 Security and safety

**Adversarial examples** (small perturbations flip predictions — still largely unsolved),
**data poisoning**, **model extraction**, **membership inference** and **training data
extraction** (models memorize; verbatim regurgitation is real), and **prompt injection**
for LLM systems (⚠️ **not solved**, and any system giving an LLM tools plus untrusted input
has this exposure).

**⚠️ `pickle` deserialization is arbitrary code execution.** Use **safetensors** for model
weights. PyTorch's `weights_only=True` default since 2.6 addresses this, but third-party
checkpoints from unknown sources remain a real supply-chain risk.
