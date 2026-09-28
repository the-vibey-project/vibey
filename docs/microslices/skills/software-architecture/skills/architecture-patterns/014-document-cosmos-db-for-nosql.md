---
id: skill-document-cosmos-db-for-nosql-4cac6b32b5
purpose: document cosmos db for nosql
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-relational-rdbms-b5902985cf"]
links: ["skill-key-value-redis-90e5ca50cb"]
---

## Document (Cosmos DB for NoSQL)

**The partition key is the single most critical and irreversible decision.** A poor partition key (low cardinality or skewed access) creates hot partitions that throttle (429s) regardless of provisioned RUs — and you **cannot change a container's partition key in place**; you must migrate.

- Five **consistency levels**: strong, bounded staleness, session (default), consistent prefix, eventual
- **Change feed**: built-in CDC
- Multi-region writes
