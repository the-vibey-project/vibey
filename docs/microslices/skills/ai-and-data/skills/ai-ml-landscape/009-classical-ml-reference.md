---
id: skill-classical-ml-reference-3f394cc82a
purpose: classical ml reference
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-mathematical-foundations-c6ba07b729"]
links: ["skill-deep-learning-foundations-22ae3d1ed1"]
---

## Classical ML Reference

### Regression & Classification
- OLS with Ridge/Lasso/ElasticNet for regularized selection
- GLMs (logistic, Poisson, negative binomial) for non-Gaussian targets
- Gaussian Process Regression for small-data + calibrated uncertainty
- Logistic regression: strong, interpretable baseline — always try it first
- SVMs (kernel trick, RBF): still win on small high-dimensional data

### Calibration
**Calibration matters in production.** Temperature scaling (post-hoc, single-parameter) for neural nets; isotonic/Platt for others. Brier score and reliability diagrams for diagnosis.

### Unsupervised & Anomaly Detection
- Clustering: k-means(++)/DBSCAN/HDBSCAN/GMM/spectral
- Dimensionality reduction: PCA/UMAP/t-SNE (UMAP preferred for preserving global structure and speed)
- Anomaly detection: isolation forest/LOF/autoencoders

### Model Selection
- Stratified/group/time-series CV to prevent leakage
- Metric choice: AUC-PR for imbalanced, MCC as balanced single number, log-loss for probabilistic
- Optuna (TPE/Bayesian) + Hyperband/ASHA for hyperparameter tuning
- **Leakage is the silent killer**: target leakage, train/test contamination via preprocessing, and temporal leakage cause the most "great offline, broken online" failures

---
