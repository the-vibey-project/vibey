---
id: skill-context-window-engineering-d9607b02e3
purpose: context window engineering
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-prompt-caching-the-cache-golden-rule-a106b67d1b"]
links: ["skill-prompt-context-compression-provider-agnostic-608d6a96ce"]
---

## Context Window Engineering

### Token Budget Allocation
**Token budget is a first-class design constraint.** Allocate explicit budgets per component:
- System prompt
- Tool definitions
- Conversation history
- Retrieved context (RAG)
- Output headroom (especially for reasoning models)

Optimize for **cost-per-task**, not tokens-saved-in-isolation.

### Conversation History Management (Cost Tiers)
1. **Naive** (full history): linear cost growth — only for short sessions
2. **Sliding window**: keep last N turns
3. **Rolling summarization** (MapReduce): summarize old turns, keep recent full
4. **Embedding-based selective retention**: retrieve most-relevant past turns
5. **Hybrid**: recent full + rolling summary + pinned facts
6. **External memory** (MemGPT/Letta): LLM-managed memory tiers; Cosmos DB/Redis/AI Search as backing store

Store session state in Azure Cosmos DB or Azure Cache for Redis. Compact conversation history infrequently at predictable boundaries (compacting breaks the stable cache prefix).

### LLMLingua Prompt Compression (Microsoft Research)
- **LLMLingua** (arXiv 2310.05736, EMNLP 2023): up to 20× compression with only ~1.5 point performance drop
- **LLMLingua-2**: 3–6× faster than LLMLingua-1; task-agnostic
- **LongLLMLingua**: improves RAG by up to 21.4% using only 1/4 of the tokens
- Stacks with caching — cache the compressed prompt
- Use when: long-doc RAG with many retrieved passages; cost-sensitive pipelines; large static context

### "Lost in the Middle"
Per Liu et al. (TACL 2024, arXiv:2307.03172): performance "significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models." Place critical information first or last. Rerank retrieved docs so the gold passage sits at an extremity.

---
