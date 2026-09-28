---
id: skill-incremental-loads-cdc-b74db18ed6
purpose: incremental loads cdc
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-pipeline-design-principles-9989b94a83"]
links: ["skill-scd2-implementation-e91c9192e2"]
---

## Incremental Loads & CDC

**Watermark-based incremental**: pull rows where `updated_at > last_watermark`. Store the watermark in the target DB audit table.

**Debezium** (dominant open-source CDC):
- Reads the database transaction log (WAL/binlog) via Kafka Connect — not polling
- Captures every insert/update/delete in order with minimal source impact
- Supports MySQL, Postgres, MongoDB, SQL Server, Oracle
- **Incremental snapshots** (v1.6+): interleaves snapshotting with streaming using watermark approach (from Netflix's DBLog paper) — no long table locks
- Note: log-based CDC on Postgres may require config changes and a restart

---
