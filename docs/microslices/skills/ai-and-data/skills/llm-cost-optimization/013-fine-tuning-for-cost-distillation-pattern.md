---
id: skill-fine-tuning-for-cost-distillation-pattern-649f1c9380
purpose: fine tuning for cost distillation pattern
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-tool-calling-cost-optimization-ac01b79fcd"]
links: ["skill-embeddings-cost-optimization-476dec2c3e"]
---

## Fine-Tuning for Cost (Distillation Pattern)

1. Set `store: true` on production frontier-model calls to capture completions
2. Accumulate hundreds–thousands of high-quality examples (minimum 10 stored completions)
3. Fine-tune a smaller model (e.g., GPT-4.1-nano) on teacher's outputs
4. Validate quality delta is acceptable before routing production traffic

**Expected result**: ~90% quality at ~10% cost.

**Azure fine-tuning specifics:**
- Training files: JSONL format; per-token training fee + hourly hosting cost for deployed custom models
- **"Fine-tune zombie" trap**: delete unused fine-tuned deployments to avoid hourly hosting cost
- Supported: gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-nano, o4-mini (Reinforcement Fine-Tuning), Llama 4 Scout
- Global Standard is the default deployment for new fine-tunes (cheaper than regional)
- Prompt caching works on fine-tuned models

---
