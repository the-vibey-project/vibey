---
id: skill-advanced-rag-patterns-35d40777d0
purpose: advanced rag patterns
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-context-assembly-generation-21b8339a4d"]
links: ["skill-rag-evaluation-489316c9f0"]
---

## Advanced RAG Patterns

### GraphRAG (Microsoft, open-sourced July 2, 2024)
**From:** "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (arXiv 2404.16130)

**Indexing:** LLM extracts entities/relationships per chunk → builds graph → partitions with Leiden algorithm hierarchically → generates community summaries bottom-up.

**Query modes:**
- **Global search**: map-reduce over community summaries; for whole-dataset/thematic questions ("top 5 themes?")
- **Local search**: entity-anchored retrieval; for specific-entity questions; faster and cheaper than global
- **DRIFT search** (late 2024): combines global+local — HyDE-based Primer phase + local refinement; produces hierarchical Q&A output

**Paper results vs vector RAG**: comprehensiveness win 72–83%, diversity 62–82%. Vector RAG scored higher only on Directness (expected — passage retriever is more targeted for local questions).

**Cost cliff**: original GraphRAG indexing was prohibitively expensive (one estimate: $33K for a 5GB legal case). Use **LazyGraphRAG** (Microsoft Research, Nov 25, 2024):
- Defers LLM use to query time; uses NLP-based extraction
- ~0.1% of full GraphRAG indexing cost (~1,000× reduction)
- Matches full GraphRAG global-search quality at >700× lower query cost
- Best for one-off queries, exploratory analysis, streaming data

**When to use GraphRAG**: multi-hop or thematic queries across large, relatively static corpus. Start with LazyGraphRAG, not full GraphRAG, unless you have high-utilization static corpus justifying expensive indexing. Never deploy on high-update or simple-factoid corpus.

### CRAG, Self-RAG, Adaptive RAG
- **CRAG** (Corrective RAG): grader LLM scores retrieved docs; if irrelevant, fall back to web search (LangGraph conditional routing)
- **Self-RAG**: model decides when to retrieve and critiques its own output (via prompting in practice)
- **Adaptive RAG**: classify query complexity → route (no-retrieval for simple factoids, single retrieval for medium, multi-step for complex)

---
