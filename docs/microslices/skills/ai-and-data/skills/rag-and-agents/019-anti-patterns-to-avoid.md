---
id: skill-anti-patterns-to-avoid-c3f0a25a8b
purpose: anti patterns to avoid
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-emerging-patterns-893d12ab17"]
links: ["skill-staged-implementation-roadmap-5678f10d22"]
---

## Anti-Patterns to Avoid

1. **Pure vector search** with no keyword/hybrid component (misses exact terms, codes, acronyms)
2. **Re-embedding unchanged documents** (deterministic; cache by content hash)
3. **Mismatched query/document embedding models** (use the same model or an asymmetric pair)
4. **Fixed-size chunking** that splits tables/clauses mid-unit (neutralizes reranker gains)
5. **Exposing >10 tools to a single agent** without intent-based gating
6. **Running LLM-generated code in-process** instead of an isolated sandbox
7. **Deploying full GraphRAG** on high-update or simple-factoid corpus — use LazyGraphRAG
8. **MTEB leaderboard as ground truth** instead of testing on your own data
9. **Shipping without a golden eval set** — never deploy RAG/agent changes without measuring against a baseline

---
