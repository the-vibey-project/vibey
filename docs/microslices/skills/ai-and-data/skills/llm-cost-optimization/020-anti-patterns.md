---
id: skill-anti-patterns-c6010a71e2
purpose: anti patterns
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-staged-implementation-roadmap-3f5b006a23"]
links: []
---

## Anti-Patterns

1. **Full history every turn** — linear cost growth; use sliding window or summarization
2. **Dynamic content before static** (e.g., timestamp in system prompt) — breaks prompt caching
3. **Frontier model for trivial tasks** — use routing
4. **Verbose tool schemas** — wastes input tokens; cache them in stable prefix
5. **Sequential calls for independent subtasks** — parallelize with `parallel_tool_calls` or asyncio
6. **JSON mode over Structured Outputs** — use `strict: true` JSON Schema instead
7. **No `max_tokens` set** — unbounded cost exposure
8. **Re-embedding unchanged documents** — cache by content hash
9. **Unsanitized injection vectors** — RAG retrieved content can carry injection payloads
10. **Optimizing without evals** — cost savings are assumed quality-neutral; they are not
11. **Ignoring reasoning token billing** — reconcile against API `usage` object and Azure invoice
12. **Using Marketplace models without checking billing coverage** — not covered by Azure credits/sponsorship
