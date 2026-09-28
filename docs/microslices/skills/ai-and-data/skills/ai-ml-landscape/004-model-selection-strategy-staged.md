---
id: skill-model-selection-strategy-staged-66b37a7e34
purpose: model selection strategy staged
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-hosted-apis-vs-open-weights-decision-rule-1034e4ac4c"]
links: ["skill-build-pattern-for-llm-applications-0189a87f68"]
---

## Model Selection Strategy (Staged)

1. **Start with hosted frontier behind an abstraction layer.** Default to strong mid-tier (Claude Sonnet-class, GPT-4.1-mini-class, Gemini Flash-class); escalate to top-tier only for hard tasks.

2. **Implement model routing** once volume justifies it. A cheap classifier sends easy queries to small/cheap models with confidence-gated escalation. RouteLLM (UC Berkeley/Anyscale/Canva, ICLR 2025) achieved 95% of GPT-4 quality using only ~26% of GPT-4 calls, with up to 85% cost reduction on MT-Bench.

3. **Move to open weights self-hosted on vLLM/SGLang** when privacy, air-gap, predictable cost at scale, or fine-tuning control becomes the binding constraint.

---
