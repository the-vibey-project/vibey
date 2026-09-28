---
id: skill-20-sources-and-method-f33a0dcc89
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-reference/SKILL.md
requires: ["skill-19-quick-reference-aef714759f"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §1 → `ml-framing-data-and-classical` (framing),
§2 → `ml-framing-data-and-classical` (leakage and splitting), §4 → `ml-deep-learning-and-training` (optimization and training fundamentals), §9 → `ml-evaluation-serving-mlops-and-safety` (evaluation),
§10 → `ml-evaluation-serving-mlops-and-safety` (debugging), §12 → `ml-evaluation-serving-mlops-and-safety`, §14.2 → `ml-evaluation-serving-mlops-and-safety`, §15 — rests on established statistics and optimization
literature, the standard references in §18, and practices that have been stable across
framework generations. Every **time-sensitive** claim (framework versions, serving-engine
comparisons, hardware specs, cost figures) was verified against a primary or near-primary
source in **August 2026** and is flagged in §17 with a decay-risk rating. Where the
literature genuinely conflicts — notably §3.1 → `ml-framing-data-and-classical`'s tabular question — §16 presents both sides
rather than picking one.

**Search log** (August 2026): PyTorch current version and release features · vLLM/SGLang/
TensorRT-LLM serving landscape and NVIDIA hardware · gradient boosting versus deep learning
on tabular data.

**Primary and near-primary sources consulted (selected):**
- **PyTorch** — the 2.13 release announcement and GitHub release notes, the 2.12 release
  blog (torchcomms migration and breaking ProcessGroup changes), the PyTorch Versions wiki,
  and the PyTorch dev-discuss release-announcement threads
- **Academic benchmarks for §3.1 → `ml-framing-data-and-classical`** — Shwartz-Ziv & Armon, *Tabular Data: Deep Learning Is
  Not All You Need* (arXiv 2106.03253); Grinsztajn et al., *Why do tree-based models still
  outperform deep learning on tabular data?* (arXiv 2207.08815); a 2025 *Neurocomputing*
  comprehensive benchmark; and 2026 comparative work identifying HistGradientBoosting's
  stability. Counter-evidence (Kadra et al. on regularized MLPs; TabR; TabPFN) noted
- **Serving and hardware** — Inference Engineering's vLLM/SGLang/TensorRT-LLM and hardware
  guides; comparative benchmarks from Particula, Yotta Labs, JarvisLabs and
  decodethefuture; Spheron on FlashInfer backend defaults; NVIDIA's AI training platform
  pages and GTC 2026 coverage on Dynamo; Thunder Compute and VRLA Tech on the TGI
  maintenance-mode transition and GPU selection
- **Economics** — GPUnex's 2026 inference-economics analysis; an arXiv study (2601.09527)
  benchmarking self-hosted inference cost parity on consumer Blackwell GPUs

**Confidence statement.** **High confidence** in §1–§5 → `ml-framing-data-and-classical`, `ml-deep-learning-and-training`, §9 → `ml-evaluation-serving-mlops-and-safety`, §10 → `ml-evaluation-serving-mlops-and-safety`, §12 → `ml-evaluation-serving-mlops-and-safety`, §14 → `ml-evaluation-serving-mlops-and-safety`, §15 and §19 —
these rest on textbook statistics, established optimization results, and practices
consistently reported across the standard references. **High confidence** in the PyTorch
2.13 details in §17, which come from PyTorch's own release notes and announcements.
**Moderate confidence** in §11.1 → `ml-evaluation-serving-mlops-and-safety`'s serving-engine performance comparisons: the throughput
numbers come from third-party benchmarks run on specific hardware with specific models and
workloads, **different benchmarks reach different conclusions**, and both engines are
evolving fast enough that a six-month-old number may be wrong — treat them as directional
and benchmark on your own workload. **Moderate confidence** in §11.4 → `ml-evaluation-serving-mlops-and-safety`'s and §17's cost
figures, which come from industry analysis rather than audited data and depend heavily on
assumptions about utilization and model choice. **Moderate confidence, deliberately hedged,
in §3.1 → `ml-framing-data-and-classical`**: the weight of independent evidence favours GBDTs on tabular data and I've said
so, but I have also cited the conflicting findings, and the *reason* the practical advice
holds (start with a GBDT, make the neural network earn its complexity) is about cost and
tuning burden as much as about raw accuracy. Hardware specifications in §13 → `ml-evaluation-serving-mlops-and-safety` come from
vendor materials and vendor performance claims (notably NVIDIA's "3× faster training") are
**vendor-measured on vendor-chosen benchmarks** and should be treated accordingly.
