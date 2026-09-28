---
id: skill-classical-ml-tabular-data-44244ce7bd
purpose: classical ml tabular data
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-reasoning-models-test-time-compute-68e64b76c1"]
links: ["skill-mathematical-foundations-c6ba07b729"]
---

## Classical ML — Tabular Data

Gradient-boosted trees remain state-of-the-art on most tabular problems. Deep learning requires more tuning and rarely wins on tabular without genuine unstructured signal.

**2025 challenger**: TabPFN (transformer tabular foundation model, published in Nature) beats GBDTs on small/medium single tables. XGBoost still wins on large tables.

**Practitioner default**: GBDT-first (LightGBM → CatBoost → XGBoost depending on data characteristics). Only reach for deep learning with genuine unstructured signal or very large data.

---
