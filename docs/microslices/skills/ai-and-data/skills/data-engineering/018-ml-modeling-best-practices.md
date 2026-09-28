---
id: skill-ml-modeling-best-practices-0d85ee4a54
purpose: ml modeling best practices
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-mlflow-production-patterns-be157f33f1"]
links: ["skill-data-mesh-what-actually-works-38b4ee810c"]
---

## ML Modeling Best Practices

### Feature Engineering
- Target encoding for high-cardinality categoricals (with CV/smoothing to prevent leakage)
- One-hot for low cardinality; embeddings for very high cardinality
- Temporal features (lags, rolling windows): build carefully to avoid leakage
- **Never compute encodings/scalers on full dataset before splitting**

### Model Validation
- **Time-series CV** (expanding/rolling window) for temporal data — never shuffle-split
- **Group-k-fold** when records cluster (same user/entity)
- Calibrate probabilities (Platt/isotonic) for reliable scores
- scikit-learn `Pipeline + ColumnTransformer`: canonical leakage guard — preprocessing fit only on training folds

### Gradient Boosting (Tabular Data Default)
All three are competitive; no significant differences under Wilcoxon–Holm analysis (arXiv 2407.00956):

| Library | Strength | Weakness |
|---|---|---|
| **LightGBM** | Fastest (~7× vs XGBoost); best for very large datasets | Leaf-wise growth overfits small data |
| **CatBoost** | Best with many categorical features (native handling); strong defaults | |
| **XGBoost** | Slight accuracy/generalization edge in some benchmarks; Kaggle workhorse | Slowest grid search on large data |

**Tuning sequence**: benchmark all three with defaults → tune the frontrunner: lower `learning_rate` + more estimators with early stopping, reduce `max_depth`/`num_leaves`, raise L1/L2, subsample.

### A/B Testing
- Pre-compute sample size from MDE, alpha, and power (typically 80%)
- **Peeking problem**: checking results repeatedly inflates Type I error
- **Fixed-horizon tests**: no peeking, decide at planned N — maximum rigor
- **Sequential testing** (O'Brien-Fleming or Pocock alpha-spending): valid peeking and early stopping
- A/A tests validate randomization
- Multi-armed bandits: good for many-armed, low-stakes optimization; not for clean causal readouts

---
