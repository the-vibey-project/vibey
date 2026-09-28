---
id: skill-tool-calling-cost-optimization-ac01b79fcd
purpose: tool calling cost optimization
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-advanced-prompt-engineering-b07ad86f03"]
links: ["skill-fine-tuning-for-cost-distillation-pattern-649f1c9380"]
---

## Tool Calling Cost Optimization

- **Write terse tool descriptions** — verbose schemas waste input tokens
- **Limit tools** — performance degrades past ~10 tools per call
- **Progressive/intent-based tool exposure** — send only relevant tools per query type
- Use `parallel_tool_calls` for independent calls (reduces round-trips)
- Cache tool definitions in the system prefix (they're stable → high cache hit rate)
- Fine-tuning with tool examples can replace verbose tool definitions at inference time

---
