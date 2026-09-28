---
id: skill-rag-retrieval-augmented-generation-1f95ecf8dd
purpose: rag retrieval augmented generation
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-cdc-change-data-capture-3405ab4c9e"]
links: ["skill-apim-ai-gateway-front-all-llm-traffic-from-day-one-fef2d50c99"]
---

## RAG (Retrieval-Augmented Generation)

### Pipeline
1. **Ingestion**: load → chunk → embed → index
2. **Retrieval**: embed query → similarity/hybrid search → retrieve context
3. **Generation**: context + query → LLM → response

### Chunking Strategies
- Fixed-size, semantic/sentence-aware, hierarchical (small-to-big), structure-aware

### Retrieval Approaches
- Dense (vector), sparse (BM25), **hybrid (RRF fusion)** — hybrid is best in practice
- **Reranking** with a cross-encoder boosts top-K precision

### Azure AI Search (Recommended)
Per Microsoft's own benchmarking: hybrid search (BM25 keyword + vector via RRF) plus a transformer-based **semantic ranker** is "the most effective retrieval engine for most scenarios."

- Semantic ranker is an L2 step that reranks the top 50 L1 results, scoring on a 0–4 scale
- Set `k`/`maxTextRecallSize` to sum ≥50 to give the reranker a full input set
- **Integrated vectorization** chunks and embeds inside the indexer pipeline

### Azure AI Foundry Evaluators (for RAG)
Microsoft's recommended RAG combination: **Retrieval + Groundedness + Relevance + Content Safety**

Available evaluators: Retrieval, Document Retrieval, Groundedness, Groundedness Pro, Relevance, Response Completeness, Coherence, Fluency, QA, Intent Resolution, Tool Call Accuracy, Task Adherence, risk/safety, textual-similarity (BLEU/ROUGE/METEOR/GLEU/F1).

**Note:** RAGAS is not a native Foundry evaluator — RAGAS integration in the Microsoft ecosystem is via MLflow on Azure Databricks.
