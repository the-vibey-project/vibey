---
id: skill-orchestration-tool-selection-33376f13a6
purpose: orchestration tool selection
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-dbt-project-structure-7397ed7111"]
links: ["skill-data-quality-layered-approach-625fecd953"]
---

## Orchestration — Tool Selection

| Tool | Best for | Weakness |
|---|---|---|
| **Airflow** | Enterprise, 100+ pipelines, 1,000+ providers (MWAA/Cloud Composer/Astronomer) | Steeper learning curve; needs running instance to test DAGs |
| **Dagster** | Greenfield/dbt-centric platforms; software-defined assets, local testing (swap Snowflake for DuckDB) | ~1/4 of Airflow's integrations |
| **Prefect** | Python-native, fastest laptop-to-production | Serverless cold starts 5–15s; near-real-time workloads feel this |

**Migration rule:** 50+ working Airflow DAGs → stay and adopt TaskFlow incrementally; Dagster migration runs ~10–20 DAGs/month via `dagster-airflow`.

---
