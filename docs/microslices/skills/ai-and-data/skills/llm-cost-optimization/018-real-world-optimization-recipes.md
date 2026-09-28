---
id: skill-real-world-optimization-recipes-fa25ed877e
purpose: real world optimization recipes
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-cost-unit-economics-ae3f1aaa90"]
links: ["skill-staged-implementation-roadmap-3f5b006a23"]
---

## Real-World Optimization Recipes

| Recipe | Expected savings | Requirement |
|---|---|---|
| **R1 — Model routing** | 60–80% on routine queries | Quality eval confirming <1–2% delta |
| **R2 — Prompt caching** | 40–50% on input tokens | Stable ≥1,024 token prefix; verify via `cached_tokens` |
| **R3 — Semantic caching** | 30–80% on repeat traffic | Low query diversity; non-personalized/non-realtime answers |
| **R4 — Batch API** | 50% at 24h SLA | Async workloads (evals, nightly processing, embedding refresh) |
| **R5 — LLMLingua compression** | Up to 20× token reduction | Long-doc RAG; accept ~1.5 point quality drop |
| **R6 — Distillation** | ~90% quality at ~10% cost | High-volume domain-specific tasks; hundreds of teacher completions |
| **R7 — PTU right-sizing** | Up to 70% vs hourly | 30–60 days telemetry; P95 hourly throughput; sustained >50% utilization |

**Stack order**: Instrument first → quick wins (caching + batch) → routing → semantic cache → PTU commitment → distillation.

---
