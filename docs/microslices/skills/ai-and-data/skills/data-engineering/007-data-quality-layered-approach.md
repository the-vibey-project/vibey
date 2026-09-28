---
id: skill-data-quality-layered-approach-625fecd953
purpose: data quality layered approach
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-orchestration-tool-selection-33376f13a6"]
links: ["skill-python-data-stack-328ad25db7"]
---

## Data Quality — Layered Approach

- **dbt tests**: shift-left checks inside transformation layer
- **Great Expectations**: 300+ expectations, automated profiling, human-readable Data Docs; expressive Python validation-as-code
- **Soda Core**: YAML-based, SQL-native, lightweight
- **Deequ** (Amazon, Spark-native): massive-scale checks without sampling
- **Pandera**: DataFrame schema validation (pandas, Polars, PySpark, Ibis backends); use for feature-engineering checks, drift detection, ETL decorators

Most mature teams combine dbt tests (model layer) + Great Expectations or Soda Core (distribution/profiling checks dbt can't express).

---
