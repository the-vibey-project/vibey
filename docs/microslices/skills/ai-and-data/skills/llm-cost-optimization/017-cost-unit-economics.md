---
id: skill-cost-unit-economics-ae3f1aaa90
purpose: cost unit economics
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-azure-monitor-metrics-reference-690c72d795"]
links: ["skill-real-world-optimization-recipes-fa25ed877e"]
---

## Cost Unit Economics

**Build cost-per-task, not cost-per-token.** RAG cost breakdown:
- Embedding (one-time per document)
- Storage
- Retrieval query embedding (per query)
- Generation (retrieved context dominates — often 80%+ of per-query cost)

**Multi-agent fan-out**: multiplies LLM calls; "your average cost per task is a lie" (GrisLabs tracked 1,127 agent runs: median $1.22, p95 $22.14 — an 18× tail). Implement:
- Per-user/session/feature anomaly detection
- Per-feature token budgets
- Hard per-run token/cost ceilings

---
