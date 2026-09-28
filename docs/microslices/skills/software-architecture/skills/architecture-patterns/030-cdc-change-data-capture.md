---
id: skill-cdc-change-data-capture-3405ab4c9e
purpose: cdc change data capture
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-lambda-vs-kappa-fcaa1ad17d"]
links: ["skill-rag-retrieval-augmented-generation-1f95ecf8dd"]
---

## CDC (Change Data Capture)
- Capture row-level DB changes as a stream for cache invalidation, search-index sync, replication, audit
- **Debezium**: de facto connector
- **Azure**: SQL/MI change tracking + ADF; **Cosmos DB change feed** (built-in); Debezium on AKS feeding Event Hubs; **Fabric Mirroring** for zero-ETL into OneLake

---

# PART 12: AI/ML ARCHITECTURE PATTERNS
