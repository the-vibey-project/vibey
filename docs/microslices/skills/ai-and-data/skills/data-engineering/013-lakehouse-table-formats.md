---
id: skill-lakehouse-table-formats-f30ad0fde3
purpose: lakehouse table formats
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-cloud-warehouse-cost-controls-033fdd1fa2"]
links: ["skill-azure-databricks-optimization-f4f2302cc8"]
---

## Lakehouse Table Formats

| Format | Best for | Notes |
|---|---|---|
| **Iceberg** | Interoperability standard; partition evolution as metadata operation | Databricks acquired Tabular (Iceberg creators); AWS S3 Tables, Snowflake Polaris catalog |
| **Delta** | Largest installed base; Microsoft Fabric default | Most large enterprises; Databricks default |
| **Hudi** | Streaming/CDC upserts (Merge-on-Read first-class) | Vendor (Onehouse) benchmarks favor it for upserts — run your own TPC-DS |

---
