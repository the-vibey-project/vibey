---
id: skill-vector-search-3bc6f56154
purpose: vector search
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-key-value-redis-90e5ca50cb"]
links: ["skill-data-lakes-lakehouses-0e973d9cf5"]
---

## Vector Search

**Full Azure menu:**
| Service | Algorithm | Notes |
|---|---|---|
| **Azure AI Search** | Hybrid BM25+vector+semantic reranker | Full retrieval stack; `vector_semantic_hybrid` is Microsoft's recommended default |
| **Cosmos DB for NoSQL** | DiskANN (GA) | Sub-20ms at scale; requires ≥1,000 vectors or falls back to full scan |
| **PostgreSQL Flexible Server + pgvector** | HNSW | Familiar SQL interface |
| **Azure SQL Database** | Native VECTOR type + `VECTOR_DISTANCE` (GA June 2025); DiskANN indexes (preview) | Co-locate with operational data |
| **Azure Cache for Redis (Enterprise)** | RediSearch vector | Ultra-low latency |

**Decision:** Full retrieval stack → AI Search. Data already in Cosmos/SQL, want no extra system → built-in vector search. Pure billion-scale vector workload → dedicated vector DB may be cheaper.
