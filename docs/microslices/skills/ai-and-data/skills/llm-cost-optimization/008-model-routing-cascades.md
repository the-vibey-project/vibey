---
id: skill-model-routing-cascades-d39b8daf17
purpose: model routing cascades
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-prompt-context-compression-provider-agnostic-608d6a96ce"]
links: ["skill-apim-ai-gateway-reference-architecture-691f919943"]
---

## Model Routing & Cascades

**The single highest-ROI lever.** Task-to-tier mapping:

| Task type | Recommended tier |
|---|---|
| Classification, extraction, simple formatting | Nano/Phi-4-class |
| Chat, summarization, standard Q&A | Mini-class |
| Complex reasoning, code refactoring, multi-step analysis | Frontier/reasoning |

### RouteLLM (UC Berkeley/Anyscale/Canva, ICLR 2025)
- Matrix-factorization routing between strong/weak models
- Achieves 95% of GPT-4 performance using 26% GPT-4 calls (~48% cheaper)
- With LLM-judge-augmented training data: 14% of total calls (75% cheaper)
- Routers generalize to new model pairs without retraining

**Microsoft Foundry Model Router caveat**: "Balanced" mode is conservative — selects within ~1–2% quality range; one Microsoft field test measured only 4.5–14.2% savings. Validate on your own traffic before projecting the 60–80% figure.

### Implementation Options
- Rule-based: query length, keyword triggers, explicit complexity signals
- Classifier-based: fine-tuned on your traffic
- RouteLLM: research-grade, open-source
- Semantic Router: embedding-based intent classification

---
