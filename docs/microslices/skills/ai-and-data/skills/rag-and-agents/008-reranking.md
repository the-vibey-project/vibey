---
id: skill-reranking-e2ac188267
purpose: reranking
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-retrieval-strategies-21e8cb5c41"]
links: ["skill-context-assembly-generation-21b8339a4d"]
---

## Reranking

**Two-stage pipeline**: retrieve top 50–200 (bi-encoder) → rerank to top 3–10 (cross-encoder).

**Expected gains**: independent benchmarks (Voyage AI) report +13.89% for Cohere rerank-2 and +11.86% for rerank-2-lite across 93 datasets on top of OpenAI text-embedding-3-large. Cohere's own materials cite 20–35%; expect 10–35% depending on baseline and domain.

| Reranker | Notes |
|---|---|
| **Cohere Rerank 3.5 / 4.0** | Best-in-class managed; multilingual 100+ languages; underperforms on identifier-heavy queries (function names, statute numbers) |
| **BGE-Reranker-v2-m3** | Self-hosted |
| **Jina Reranker v2** | 8K context |
| **FlashRank** | CPU; lightweight |
| **ColBERT/RAGatouille** | Late interaction; good when exact term matching matters |
| **Azure AI Search semantic ranker** | Microsoft-trained cross-encoder (Bing corpus); rescores top 50; returns `@search.rerankerScore` 0–4; score below ~1.0 signals weak match |

**Azure semantic ranker**: passes up to 2,048 tokens per doc (raised from 256 in Nov 2024). Order fields in semantic configuration by priority — long fields are trimmed.

---
