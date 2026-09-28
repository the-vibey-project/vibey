---
id: skill-rag-fundamentals-6f3492eac5
purpose: rag fundamentals
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-the-decision-framework-1601e239ac"]
links: ["skill-document-parsing-honest-comparison-b0d0c2ee35"]
---

## RAG Fundamentals

**Four problems RAG solves:**
1. Hallucination (grounds answers in retrieved documents)
2. Knowledge cutoff (retrieves current private data)
3. Private-data access (indexes your corpus)
4. Verifiable sourcing (enables citations)

**The full pipeline:** ingestion → chunking → embedding → indexing → query processing → retrieval → reranking → context assembly → generation

**RAG vs Fine-tuning vs Long-context:**
- **RAG**: dynamic/proprietary knowledge needing citations; audit trail
- **Fine-tuning**: changing behavior, format, tone, domain style
- **Long-context stuffing**: single-document deep reasoning where the whole doc fits; no extra infra

They combine — fine-tune for domain language, RAG for facts.

**"Lost in the middle" (Liu et al., TACL 2024):** performance degrades significantly when relevant information is in the middle of long contexts, even for explicitly long-context models. Critical info should be first or last. A 1M-token window is not a license to fill it.

**Quality framework — the "3 C's":**
- **Coverage**: right docs are indexed
- **Correctness**: retrieval finds them
- **Coherence**: generation uses them faithfully

---
