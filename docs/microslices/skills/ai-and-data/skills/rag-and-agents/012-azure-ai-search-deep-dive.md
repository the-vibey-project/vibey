---
id: skill-azure-ai-search-deep-dive-91a7480313
purpose: azure ai search deep dive
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-rag-evaluation-489316c9f0"]
links: ["skill-ai-agent-fundamentals-b3879d5844"]
---

## Azure AI Search — Deep Dive

### Tiers
Free (3 indexes, 50MB) → Basic → Standard S1/S2/S3 → Storage-Optimized L1/L2. New Serverless (Compute Unit-based) model rolling out.

### Vector Configuration
- HNSW params: `m`, `efConstruction`, `efSearch`, metric (cosine/euclidean/dotProduct)
- Exhaustive KNN for small indexes
- Scalar/binary quantization with rescoring/oversampling for storage savings

### Hybrid + Semantic Setup
```
vectorSearch + text search → RRF fusion → queryType: semantic → semantic reranker
```
- `vectorFilterMode`: preFilter (accurate, slower) or postFilter (fast, can under-return)
- `queryType: semantic` + `semanticConfiguration` + optional `answers`/`captions`

### Integrated Vectorization
Drives auto-embedding via indexer skillsets calling Azure OpenAI. A query-time **vectorizer** removes app-side embedding code. **Index projections** create chunk + parent indexes from one document. **Index aliases** enable blue-green zero-downtime reindexing.

### Security
- Managed identity (Search → Azure OpenAI keyless)
- Private endpoints, CMK, RBAC (Search Service Contributor, Search Index Data Contributor/Reader)
- **Document-level access control** via `search.in(group_ids,...)` security trimming

### Foundry IQ (Successor to "On Your Data")
- Reusable, topic-centric knowledge base with automatic indexing/vectorization/enrichment
- Sources: Blob, OneLake, SharePoint, existing indexes, web (via Grounding with Bing)
- Document-level ACL + Purview sensitivity labels
- Microsoft reports +36% improvement in RAG answer quality (vs brute-force searching all sources)
- Exposes MCP endpoint (`/knowledgebases/<kb>/mcp?api-version=2025-11-01-preview`)

### "On Your Data" Deprecation
Microsoft stopped onboarding new models. Only supports GPT-4o (2024-05-13, 2024-08-06, 2024-11-20) and GPT-4o-mini (2024-07-18). Migration path: **Foundry Agent Service with Foundry IQ** (or custom Azure AI Search RAG pipeline — only managed On Your Data workloads need to migrate).

---
