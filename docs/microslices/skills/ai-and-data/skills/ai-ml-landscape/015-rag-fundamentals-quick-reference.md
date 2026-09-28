---
id: skill-rag-fundamentals-quick-reference-e009d8b375
purpose: rag fundamentals quick reference
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-evaluation-benchmark-skepticism-4c1574b63b"]
links: ["skill-agent-stack-mcp-ed82f9638f"]
---

## RAG Fundamentals (Quick Reference)

**Production default** (2026): hybrid search (BM25 + dense via RRF) + cross-encoder reranking + parent-child chunking.

**Anthropic Contextual Retrieval** (Sept 2024): prepend LLM-generated chunk summary before embedding/indexing.
- Contextual Embeddings alone: 35% reduction in retrieval failure (5.7%→3.7%)
- + Contextual BM25: 49% reduction (→2.9%)
- + Reranking: 67% reduction (→1.9%)

**RAG vs fine-tuning vs long-context:**
- RAG: dynamic/proprietary knowledge with citations
- Fine-tuning: changing behavior/format/tone/domain style
- Long-context: single-document deep reasoning where doc fits
- They combine

---
