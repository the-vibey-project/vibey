---
id: skill-vector-databases-honest-selection-guide-c0719ac20d
purpose: vector databases honest selection guide
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-embedding-models-2026-fe4d373f9b"]
links: ["skill-retrieval-strategies-21e8cb5c41"]
---

## Vector Databases — Honest Selection Guide

### ANN Index Types
- **HNSW**: graph, in-memory, top performance/recall, high RAM; tune `M`, `efConstruction`, `efSearch`
- **IVF / IVF+PQ**: partitioned + compressed; large-scale (billions with limited RAM)
- **DiskANN/Vamana**: disk-resident for billions of vectors; powers Azure Cosmos DB and Azure SQL

### Database Selection (2026)

| DB | Strength | Weakness |
|---|---|---|
| **Pinecone** | Zero-ops managed | Can't tune HNSW parameters |
| **Qdrant** (Rust) | Best-in-class filtered search, quantization | Self-host/cloud — ops burden if self-hosted |
| **Weaviate** | Best native hybrid search (BlockMax WAND GA 2025) | |
| **Milvus/Zilliz** | Billion-scale | Heavy ops (Kafka/MinIO/etcd) |
| **Chroma** | Prototyping | No native hybrid search |
| **LanceDB** | Embedded + columnar; native hybrid | |
| **pgvector** | Good enough under ~10M vectors if already on Postgres | Query planner can choose seqscan on filtered queries; degrades past 10M |

**pgvector production note**: HNSW since 0.5.0 matches dedicated DBs at 1M scale. Use `SET enable_seqscan=off` or pgvectorscale's StreamingDiskANN for filtered queries. At 50M vectors: Qdrant ~41 QPS vs pgvectorscale ~471 QPS at 99% recall.

### Azure-Native Vector Stores
- **Azure AI Search**: vector + hybrid (BM25+vector via RRF) + semantic reranker + integrated vectorization + scalar/binary quantization — the Azure-native answer
- **Azure Cosmos DB (NoSQL) with DiskANN** (GA): <20ms latency over 10M vectors; ~43× lower query cost vs Pinecone and ~12× vs Zilliz serverless; co-locates vectors with operational data
- **Azure SQL**: native VECTOR type + VECTOR_DISTANCE
- **Azure Cache for Redis Enterprise**: low-latency caching + semantic caching

---
