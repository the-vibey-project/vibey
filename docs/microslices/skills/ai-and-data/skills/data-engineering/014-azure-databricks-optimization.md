---
id: skill-azure-databricks-optimization-f4f2302cc8
purpose: azure databricks optimization
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-lakehouse-table-formats-f30ad0fde3"]
links: ["skill-schema-evolution-data-contracts-3628ce5b27"]
---

## Azure Databricks Optimization

- `OPTIMIZE`: compacts small files (~1GB target)
- `ZORDER BY`: co-locates data for high-cardinality filter columns
- `VACUUM`: removes unreferenced files (default 7-day retention via `delta.deletedFileRetentionDuration`)
- **Liquid clustering** (`CLUSTER BY`, GA DBR 15.2+): redefine clustering keys without rewriting data
- **Automatic liquid clustering** (`CLUSTER BY AUTO`, DBR 15.4+) + **predictive optimization**: Unity Catalog auto-selects keys and runs OPTIMIZE/VACUUM/ANALYZE on serverless compute
- Limit clustering to 1–4 high-value filter/join columns; don't partition tables under ~1TB

---
