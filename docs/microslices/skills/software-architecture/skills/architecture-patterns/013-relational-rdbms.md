---
id: skill-relational-rdbms-b5902985cf
purpose: relational rdbms
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-event-streaming-kafka-pattern-e7ec7e8967"]
links: ["skill-document-cosmos-db-for-nosql-4cac6b32b5"]
---

## Relational (RDBMS)

**Azure services:**
- **Azure SQL Database**: DTU / vCore / serverless / **Hyperscale** (>100 TB)
- **Azure SQL Managed Instance**: near-full SQL Server compat for lift-and-shift
- **PostgreSQL Flexible Server**: zone-redundant HA, read replicas, **built-in PgBouncer** (must be explicitly enabled)
- **MySQL Flexible Server**

**Production gotchas:**
- Azure SQL serverless auto-pause causes cold-start latency on first connection after idle
- **Connection pooling is mandatory at scale** — exhaustion is a top outage cause
- PostgreSQL Flexible Server's built-in PgBouncer must be explicitly enabled
