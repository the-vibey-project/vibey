---
id: skill-12-mlops-and-reproducibility-5c07757fa1
purpose: 12 mlops and reproducibility
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-evaluation-serving-mlops-and-safety/SKILL.md
requires: ["skill-11-inference-and-serving-9ddb9438ae"]
links: ["skill-13-hardware-and-cost-8ffda29c98"]
---

## §12. MLOps and Reproducibility

### 12.1 Reproducibility

**[DURABLE] Bit-exact reproducibility on GPU is achievable but costly**, and most teams
should aim for *statistical* reproducibility instead: seed everything (Python, NumPy,
framework, dataloader workers), pin all versions and record them, version data and code
together, log the full config, and **report variance across seeds rather than a single
run**. Full determinism requires deterministic algorithms (`torch.use_deterministic_algorithms`),
disabling cuDNN benchmarking, and fixed dataloader ordering — and it will slow you down.

**Version the data.** Model artifacts without the exact training data are not reproducible,
and "we retrained and got different numbers" is otherwise unresolvable.

### 12.2 The pipeline

```
data ingestion → validation → feature engineering → training → EVALUATION GATE
  → registry → deployment (shadow → canary → full) → MONITORING → retraining
```
**[DURABLE] The evaluation gate and monitoring are the parts people skip**, and they're
the parts that prevent silent disasters.

**Feature stores** solve a real problem — **training/serving skew**, where the features
computed at training time differ subtly from those computed at inference. **⚠️ This is one
of the most common and hardest-to-find production bugs**, and if you compute features in
two different codepaths you will eventually have it.

### 12.3 Monitoring

Monitor, in roughly this priority order: **prediction distribution** (drifts first and
cheapest to watch), **input feature distributions** (PSI, KL divergence), **actual
performance** where labels eventually arrive, **latency and throughput**, **error rates**,
and **business metrics** (the only ones that ultimately matter).

**[DURABLE] Models degrade. Plan for retraining from day one** — trigger it on a schedule,
on drift detection, or on performance drop. And **keep the ability to roll back to the
previous model instantly**; a bad model deploy is an outage.

---
