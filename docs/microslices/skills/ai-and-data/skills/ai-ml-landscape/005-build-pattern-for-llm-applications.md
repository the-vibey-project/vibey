---
id: skill-build-pattern-for-llm-applications-0189a87f68
purpose: build pattern for llm applications
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-model-selection-strategy-staged-66b37a7e34"]
links: ["skill-reasoning-models-test-time-compute-68e64b76c1"]
---

## Build Pattern for LLM Applications

**Prompting → RAG → Fine-tuning (in that order)**

- **Few-shot prompting** for behavioral change
- **RAG** for dynamic/factual/auditable knowledge — use hybrid retrieval (BM25 + dense) + reranking + contextual retrieval
- **Fine-tune** (LoRA/QLoRA) only for consistent format/style/jargon or cost reduction
- **GRPO/DPO** only when you have verifiable rewards or preference data and a reasoning/behavior target

---
