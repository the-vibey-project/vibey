---
id: skill-staged-implementation-roadmap-3f5b006a23
purpose: staged implementation roadmap
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-real-world-optimization-recipes-fa25ed877e"]
links: ["skill-anti-patterns-c6010a71e2"]
---

## Staged Implementation Roadmap

**Stage 1 — Instrument before optimizing (week 1).** Deploy APIM as AI gateway with `llm-emit-token-metric` (dimensions: team/app/user). Enable diagnostic settings → Log Analytics. Tag every deployment by feature. Compute cost-per-task on your top 3 features. Threshold: attribute >90% of spend to a feature/team.

**Stage 2 — Quick wins (weeks 2–3).** (a) Restructure prompts for stable ≥1,024-token prefix; confirm `cached_tokens` > 0. (b) Cap `max_tokens` (600–800 chat). (c) Move async workloads to Batch API. (d) Cache static-doc embeddings by content hash. Expected: 30–50% reduction.

**Stage 3 — Model routing (weeks 4–6).** Default to mini/nano-class; build rule- or classifier-based router escalating on complexity/low-confidence. Re-run evals to confirm no quality regression. Expected: additional 40–70% on routine traffic. Hold routing if quality delta exceeds 1–2 eval points.

**Stage 4 — Semantic caching + compression (weeks 6–8).** Add APIM semantic cache (Redis Enterprise) for FAQ/support traffic. Apply LLMLingua to long-doc RAG passages. Threshold: only where query diversity is low and answers aren't personalized/real-time.

**Stage 5 — PTU commitment (after 30–60 days telemetry).** Pull P95 hourly throughput. If GPT-4o-class monthly volume >150–200M tokens AND sustained utilization >50%: deploy PTU for average load, enable spillover for peaks, buy 1-month reservation first, then 1-year once steady state confirmed.

**Stage 6 — Distillation (ongoing).** Set `store: true` for high-volume domain-specific tasks. Accumulate hundreds–thousands of frontier completions. Fine-tune nano/mini behind a quality gate. Delete idle fine-tuned deployments.

**Re-evaluate model selection quarterly.** Prices and quality move fast; a model that was your only option may now be 5× pricier than a newer SKU within 1–2 eval points.

---
