---
id: skill-1-framing-a6f7c9452e
purpose: 1 framing
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-framing-data-and-classical/SKILL.md
requires: ["skill-0-routing-0e84aa9eda"]
links: ["skill-2-data-fd2352b880"]
---

## §1. Framing

### 1.1 When not to use ML

**[DURABLE] The most valuable ML judgment is recognizing the problems that don't need it.**
Don't use ML when:
- **Rules work.** If the logic is expressible in a hundred lines of `if` statements, write
  them. They're debuggable, auditable, and don't drift.
- **You don't have data**, or you can't get labels at reasonable cost.
- **You can't tolerate being wrong** and there's no fallback path.
- **The relationship you're modeling doesn't exist.** ML finds patterns; it also
  hallucinates them from noise.
- **You need a causal answer** and only have observational data. **⚠️ Prediction ≠ causation
  is the most expensive confusion in applied ML** — a model that predicts churn well tells
  you nothing about what intervention reduces churn.
- **Requirements change faster than you can retrain.**

### 1.2 Framing the problem properly

```
business objective  →  ML task  →  metric  →  data  →  baseline  →  model
       ↑                                                              |
       └──────────────── does the metric actually move it? ───────────┘
```

**[DURABLE] Always build the dumb baseline first**: predict the majority class, predict the
mean, use last week's value, use a linear model, use the existing heuristic. **If your
neural network doesn't beat the baseline by a margin that matters, you've learned
something important and cheap.** A shocking number of published and deployed models don't.

**Frame the task honestly**: supervised (classification, regression, ranking), unsupervised
(clustering, dimensionality reduction, density estimation), self-supervised (the pretraining
paradigm), reinforcement learning (⚠️ expensive, sample-hungry, hard to debug — often the
wrong tool for a problem that could be supervised), or **not-ML** (§1.1).

**Define the deployment constraint before you model**: latency budget, throughput,
memory, cost per prediction, retraining cadence, explainability requirement, and what
happens when the model is wrong. **⚠️ A model that can't meet the latency budget is a
research artifact**, and finding that out at the end is a common and avoidable waste.

---
