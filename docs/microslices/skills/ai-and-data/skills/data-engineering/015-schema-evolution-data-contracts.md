---
id: skill-schema-evolution-data-contracts-3628ce5b27
purpose: schema evolution data contracts
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-azure-databricks-optimization-f4f2302cc8"]
links: ["skill-feature-stores-012d8cc2ed"]
---

## Schema Evolution & Data Contracts

- Use a schema registry (Confluent) with Avro for Kafka to enforce backward/forward compatibility
- **Open Data Contract Standard (ODCS) v3.1.0** (Apache 2.0, maintained by Bitol under Linux Foundation AI & Data): machine-readable producer-consumer agreements covering schema + semantics + SLAs
- **Data Contract CLI**: lint, test against Snowflake/BigQuery/Databricks, detect breaking changes, export to dbt/Avro/JSON Schema
- **Rule of thumb**: one person → skip the contract; two+ teams depend on it in production → write one

---
