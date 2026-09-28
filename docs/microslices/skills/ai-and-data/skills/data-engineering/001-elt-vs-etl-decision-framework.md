---
id: skill-elt-vs-etl-decision-framework-cfd0885cd3
purpose: elt vs etl decision framework
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: []
links: ["skill-pipeline-design-principles-9989b94a83"]
---

## ELT vs ETL — Decision Framework

**ELT is the production default** on modern cloud warehouses (Snowflake, BigQuery, Databricks). Load raw data first, transform in-warehouse with dbt. Storage/compute decoupling makes this cheaper and operationally simpler than a separate transformation tier.

**ETL still wins when:**
- Compliance requires pre-load masking/tokenization (HIPAA, PCI DSS)
- Source data must be filtered before reaching governed storage
- Destination is an operational system, not a warehouse

**ELT advantages:** preserves raw data for reprocessing when business logic changes; no transformation infrastructure to manage; one pipeline to operate.

---
