---
id: skill-sql-cte-best-practices-f41e989296
purpose: sql cte best practices
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-batch-vs-streaming-decision-575c4e0f62"]
links: ["skill-cloud-warehouse-cost-controls-033fdd1fa2"]
---

## SQL & CTE Best Practices

### CTE vs subquery vs temp table
- CTEs and subqueries are **performance-equivalent** in modern engines (Postgres 12+, BigQuery, Snowflake)
- CTEs win on readability and avoiding repeated scans
- Postgres ≤11 materialized CTEs (optimization fence); Postgres 12+ inlines them
- Snowflake: CTE referenced twice scanned 1.3MB vs 2.7MB for repeated subquery
- Temp tables benefit from indexing for complex multi-step manipulation

### Window Functions
- `ROW_NUMBER` (unique sequential), `RANK` (gaps on ties), `DENSE_RANK` (no gaps)
- `LAG`/`LEAD` (prior/next row), `FIRST_VALUE`/`LAST_VALUE`
- **Critical**: `ROWS` vs `RANGE` frames — RANGE includes all peer rows with equal ordering values; the default `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` can produce surprising results with ties

### Query Optimization
- Read EXPLAIN ANALYZE plans; confirm partition pruning fires and predicate pushdown reaches scans
- **BigQuery**: partition on DATE/TIMESTAMP/INT, cluster on high-cardinality filter columns; filtering one month of 5-year table scans ~1/60th
- **Snowflake**: automatic micro-partitioning with min/max metadata; manual clustering keys for large frequently-filtered tables (50–70% data reduction); note clustering/elimination uses only first ~5 characters (so YYYYMMDD clusters by YYYYM effectively)

### Anti-patterns
- Correlated subqueries (re-execute per outer row — rewrite as joins)
- `DISTINCT` to paper over join fan-out (fix the join grain instead)
- Implicit type coercion (silently kills index/partition usage)
- `SELECT *` on columnar stores (BigQuery bills full column scan regardless of LIMIT)

---
