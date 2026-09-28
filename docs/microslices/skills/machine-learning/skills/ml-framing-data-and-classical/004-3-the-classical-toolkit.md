---
id: skill-3-the-classical-toolkit-eb00bbd306
purpose: 3 the classical toolkit
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-framing-data-and-classical/SKILL.md
requires: ["skill-2-data-fd2352b880"]
links: []
---

## §3. The Classical Toolkit

### 3.1 Gradient boosting — still the tabular default

**[DURABLE, and it's the most useful practical fact in this document.]** For structured /
tabular data, **gradient-boosted decision trees remain the strongest default**, and this
has survived a decade of attempts to unseat them. The evidence is consistent across
independent benchmarks: Shwartz-Ziv & Armon ("Tabular Data: Deep Learning Is Not All You
Need") found deep models weaker than XGBoost, and that deep models only beat XGBoost when
*ensembled with* it; Grinsztajn et al. ("Why do tree-based models still outperform deep
learning on tabular data?") found the same across many datasets.

**Why trees win here [DURABLE]**: tabular features have no spatial or sequential structure
to exploit, they're heterogeneous in scale and type, trees handle missing values and
categoricals natively, they're robust to uninformative features, they need far less tuning,
and they train fast on CPU. The honest counterweight from the same literature: **trees
generalize less well to diverse unseen data and are less robust to distribution shift than
deep models**, and well-regularized MLPs beat GBDTs in some studies (Kadra et al.) — so
the literature genuinely conflicts at the margins.

**[VERSIONED] The three libraries**: **XGBoost** (mature categorical support,
terabyte-scale external-memory training), **LightGBM** (leaf-wise growth, histogram-based
splits — fastest and most memory-efficient on large data), and **CatBoost** (best
out-of-the-box performance, especially with categorical-heavy data, via ordered target
encoding). Scikit-learn's **HistGradientBoosting** has been identified in comparative work
as **the most stable across datasets** with good performance and computational efficiency.

**⚠️ The performance gap between the three has narrowed to the point of near-irrelevance.
Feature engineering and proper tuning matter far more than which one you pick.** Start with
whichever you know; switch only for a specific reason (huge data → LightGBM; heavy
categoricals → CatBoost).

### 3.2 The rest of the classical toolkit

**Linear/logistic regression** — still the right answer surprisingly often. Interpretable,
fast, well-calibrated, and an honest baseline. **Regularization**: L2 (ridge — shrinks),
L1 (lasso — sparsifies and selects), elastic net.
**Random forests** — lower ceiling than boosting but nearly tuning-free and hard to
overfit; a good sanity check.
**SVMs** — largely superseded, still fine on small high-dimensional data.
**k-NN** — a genuinely useful baseline, and the conceptual core of retrieval and embeddings.
**Clustering** — k-means (⚠️ assumes spherical, equal-variance clusters; choosing k is not
a solved problem), DBSCAN/HDBSCAN (density-based, finds arbitrary shapes, handles noise),
hierarchical, Gaussian mixtures.
**Dimensionality reduction** — PCA (linear, fast, interpretable variance), UMAP and t-SNE
for **visualization only**. **⚠️ Never interpret distances or cluster sizes in a t-SNE or
UMAP plot as meaningful** — this is one of the most common misreadings in applied ML.
**Calibration** — Platt scaling, isotonic regression. **[DURABLE] If your downstream
decision uses the probability rather than the argmax, you must calibrate**, and most people
don't. Boosted trees and neural nets are both typically miscalibrated out of the box.
