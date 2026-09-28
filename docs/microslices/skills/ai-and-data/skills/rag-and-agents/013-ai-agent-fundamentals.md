---
id: skill-ai-agent-fundamentals-b3879d5844
purpose: ai agent fundamentals
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-azure-ai-search-deep-dive-91a7480313"]
links: ["skill-agent-frameworks-c7f465a44d"]
---

## AI Agent Fundamentals

**Agent = LLM + tools + memory + planning loop**

**Base pattern**: ReAct (Yao et al., 2022) — interleaved Thought/Action/Observation. Foundation of modern tool-using agents implemented via function calling.

**When to use agents vs deterministic workflows:**
- Known steps, no dynamic planning → deterministic workflow
- Dynamic planning required → agent

**Top failure modes**: tool-call errors, infinite loops, context loss, hallucinated tool calls, over-planning.

### Tool Calling Best Practices
- Validate inputs with Pydantic
- Use `parallel_tool_calls` for independent calls
- Performance degrades above ~10 tools — use progressive/intent-based tool exposure
- Cache tool definitions in the system prefix (stable prefix for caching)

### Memory Tiers
| Tier | Storage | Use |
|---|---|---|
| In-context (working) | Token window | Current task context |
| Episodic | Vector DB (Cosmos DB, Redis, AI Search) | Past conversations |
| Semantic | Long-term facts store | Knowledge base |
| Procedural | Fine-tuning / system prompt | Action patterns |

**Production memory (Azure):** Cosmos DB for durable history, Redis for fast recent, AI Search for semantic retrieval. Foundry Agent Service Memory (public preview) for automatic extraction/consolidation.

---
