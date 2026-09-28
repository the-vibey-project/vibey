---
id: skill-9-evaluation-bfbd2388f7
purpose: 9 evaluation
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-evaluation-serving-mlops-and-safety/SKILL.md
requires: []
links: ["skill-10-debugging-training-ecd081429a"]
---

## §9. Evaluation

**[DURABLE] This section is where most projects actually fail, and it fails quietly.**

### 9.1 Metrics

**⚠️ Accuracy is almost always the wrong metric.** On a 99:1 imbalanced problem, predicting
the majority class gets 99% accuracy and is useless.

| Task | Metrics |
|---|---|
| **Binary classification** | Precision, recall, F1, **PR-AUC** (better than ROC-AUC under heavy imbalance), ROC-AUC, MCC, and the **confusion matrix — always look at it** |
| **Multi-class** | Macro (treats classes equally) vs. micro (weights by frequency) vs. weighted — **say which you used; they disagree substantially** |
| **Regression** | MAE (robust), RMSE (penalizes large errors), MAPE (⚠️ breaks near zero, asymmetric), R² |
| **Ranking / retrieval** | NDCG, MRR, MAP, recall@k, precision@k |
| **Probabilistic** | **Log loss, Brier score, calibration curves** — use these when the probability matters |
| **Generative / LLM** | Task-specific benchmarks, human eval, LLM-as-judge (⚠️ §9.3), pairwise preference |

**[DURABLE] Choose the metric from the decision it informs.** If false negatives cost 100×
false positives, optimize for that, and **tune the decision threshold explicitly** — it's a
free parameter most people leave at 0.5 for no reason.

### 9.2 Doing it honestly

- **One test-set evaluation.** Every additional look is leakage (§2.1 → `ml-framing-data-and-classical`).
- **Report variance**, not a point estimate. Multiple seeds, confidence intervals,
  bootstrapping. **⚠️ A great deal of reported "improvement" in ML is within seed noise**,
  and the field's reproducibility problems are substantially this.
- **Compare against a strong baseline**, tuned as carefully as your method. An untuned
  baseline is not a comparison.
- **Slice your metrics.** Aggregate performance hides systematic failure on subgroups —
  by user segment, geography, device, class, time period. **This is both an accuracy
  practice and a fairness practice** (§14.2).
- **Evaluate on distribution shift** you expect in production: a future time period, a new
  region, a new source.
- **Look at the errors.** Sample 50 mistakes and read them. **Consistently the highest
  information-per-minute activity in applied ML**, and consistently skipped.

### 9.3 Evaluating generative models

Hard, and getting harder. **Benchmark contamination** is pervasive — test sets leak into
pretraining corpora, so public benchmark scores are systematically optimistic.
**LLM-as-judge** is practical and scalable but carries **position bias, verbosity bias,
and self-preference bias**; mitigate by randomizing order, using multiple judges, and
calibrating against human labels on a subset. **Build a private eval set from your actual
task**, hold it out, and version it — this beats any public benchmark for deciding whether
your system works.

---
