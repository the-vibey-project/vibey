---
id: skill-cloud-warehouse-cost-controls-033fdd1fa2
purpose: cloud warehouse cost controls
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-sql-cte-best-practices-f41e989296"]
links: ["skill-lakehouse-table-formats-f30ad0fde3"]
---

## Cloud Warehouse Cost Controls

### Snowflake
- **Auto-suspend at 60s** for ETL/short bursts; 5–10 min for cache-sensitive BI
- Enable auto-resume; use **Economy scaling policy** for batch to avoid cluster thrashing
- Multi-cluster scales out for concurrency, not single-query speed
- Capacity pricing (1–3 yr) saves ~15–25% vs on-demand
- **Cost killers**: zombie warehouses (`AUTO_SUSPEND=0`), over-provisioned dev XL warehouses, excessive Time Travel retention on truncate-reload tables, runaway reclustering on high-churn tables

### BigQuery
- On-demand: $6.25/TiB scanned (first 1 TiB/month free); `SELECT *` on 10TB = $62.50; LIMIT does not reduce cost
- Editions (Standard/Enterprise/Enterprise Plus) charge per slot-hour; autoscaling GA Feb 2025
- Break-even from on-demand to slots: ~300–500 TiB/month steady scanning
- Use `INFORMATION_SCHEMA.JOBS` / `JOBS_TIMELINE` for cost attribution
- Tables untouched 90 days → long-term storage at half price automatically

### Azure / Microsoft Fabric
- **Fabric Lakehouse** (Spark-primary) vs **Fabric Warehouse** (T-SQL-primary, full read/write)
- All data in OneLake (Delta Parquet) — Spark notebooks, T-SQL, and Power BI Direct Lake read the same table without copies
- Synapse dedicated pool → Fabric Warehouse migration: ~30–50% cost reduction vs always-on Synapse; expect 4–8 weeks per pool
- Databricks: reserved/committed compute + predictive optimization + right-sized clusters = 30–70% savings

---
