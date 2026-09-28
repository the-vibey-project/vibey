---
id: skill-16-contested-questions-ade82d56c5
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-reference/SKILL.md
requires: ["skill-15-anti-patterns-6ccbadc07e"]
links: ["skill-17-currency-snapshot-verified-august-2026-4b58279b13"]
---

## §16. Contested Questions

**16.1 Deep learning vs. GBDTs on tabular data.** §3.1 → `ml-framing-data-and-classical`. The weight of independent benchmark
evidence favours trees, but the literature genuinely conflicts — some studies find
well-regularized MLPs competitive, ensembles of both usually beat either alone, and trees
are documented as generalizing less well to unseen distributions and being less robust to
uninformative features. **The practical position — start with a GBDT, and prove a neural
network earns its complexity — is well-supported.**

**16.2 Scaling laws vs. diminishing returns.** *For scaling*: the empirical laws have held
remarkably well and predicted capabilities. *Against*: data is finite, compute costs are
enormous, and returns on some capabilities appear to be flattening. Post-training and
inference-time compute have absorbed much of the recent progress, which is itself evidence
about pretraining's marginal returns.

**16.3 PyTorch vs. JAX.** *PyTorch*: dominant ecosystem, easier debugging, most models
ship here first. *JAX*: functional purity, superior compilation and TPU story, better for
large-scale research where transformations compose. **Most people should use PyTorch; JAX
is a defensible choice for a team that will use its strengths.**

**16.4 Is benchmark progress real?** Contamination, overfitting to leaderboards, and the
gap between benchmark scores and task performance are all documented. **The defensible
position: benchmarks are directionally useful and precisely misleading**, which is why §9.3 → `ml-evaluation-serving-mlops-and-safety`
recommends a private eval set.

**16.5 Bigger models vs. better data.** Increasing evidence that data quality and curation
give more per dollar than parameter count, especially in post-training. **Not settled**, but
the direction of practitioner opinion has moved decisively toward data.

**16.6 How much MLOps tooling.** *For*: reproducibility, monitoring, and safe deploys are
real needs. *Against*: enormous accidental complexity, and many teams build a platform
before they have a model worth deploying. **Start with experiment tracking, versioned data,
and monitoring; add the rest when it hurts.**

**16.7 Open-weight vs. API models.** *Open*: control, privacy, no per-token cost at volume,
customization. *API*: no ops, frontier capability, elastic. **The break-even is real and
computable** (§11.4 → `ml-evaluation-serving-mlops-and-safety`) — and it depends almost entirely on utilization, not on ideology.

---
