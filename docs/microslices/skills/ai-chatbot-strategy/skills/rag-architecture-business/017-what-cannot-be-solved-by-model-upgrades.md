---
id: skill-what-cannot-be-solved-by-model-upgrades-2e63a7440b
purpose: what cannot be solved by model upgrades
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/rag-architecture-business/SKILL.md
requires: ["skill-evaluation-framework-for-rag-quality-b0f323c244"]
links: []
---

## What Cannot Be Solved by Model Upgrades

Spending budget on model upgrades while neglecting data curation and evaluation frameworks consistently underperforms the opposite investment strategy.

The performance hierarchy for RAG chatbots:
1. **Knowledge base quality** — the upper bound of accuracy is set here
2. **Retrieval pipeline engineering** — the layer most often responsible for production failures
3. **Data preparation** — chunking, normalization, and consistency directly determine retrieval precision
4. **Embedding model calibration** — domain-specific fine-tuning improves accuracy by ~25% over generic embeddings
5. **Model selection** — matters for cost and language quality; rarely the performance bottleneck in well-engineered systems

Building a chatbot that lasts is not primarily a technology problem. It is a knowledge problem: the organizations that extract durable value from custom AI chatbots are the ones that have invested in the quality and specificity of the knowledge those chatbots operate on, and that continue to update and refine that knowledge as their business evolves.
