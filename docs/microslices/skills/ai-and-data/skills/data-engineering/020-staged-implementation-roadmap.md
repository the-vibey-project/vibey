---
id: skill-staged-implementation-roadmap-2f911cf846
purpose: staged implementation roadmap
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-data-mesh-what-actually-works-38b4ee810c"]
links: []
---

## Staged Implementation Roadmap

**Stage 1 (weeks 0–8):** ELT on cloud warehouse + dbt (staging/intermediate/marts). Enable cost guardrails: Snowflake auto-suspend 60s + Economy; BigQuery partitioning/clustering; Databricks Unity Catalog + predictive optimization. Add dbt tests on every model.

**Stage 2 (months 2–4):** Layer Great Expectations or Soda Core for distribution/profiling checks. Data contracts (ODCS + Data Contract CLI) for datasets two+ teams depend on. Deploy orchestrator matched to team. SCD2 via dbt snapshots or two-step MERGE.

**Stage 3 (months 4–8):** Replace pandas bottlenecks with Polars/DuckDB before reaching for Spark — only adopt Spark when data genuinely exceeds single-node memory. CDC via Debezium with incremental snapshots. Streaming only where sub-second latency drives business action.

**Stage 4 (months 6–12):** scikit-learn Pipeline + ColumnTransformer to prevent leakage; time-series/group CV; MLflow Registry aliases (champion/challenger). Gradient boosting (benchmark LightGBM/CatBoost/XGBoost). Feature store only when reuse and training-serving skew are real pain points.
