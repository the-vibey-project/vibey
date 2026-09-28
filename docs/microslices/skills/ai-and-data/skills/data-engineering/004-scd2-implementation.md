---
id: skill-scd2-implementation-e91c9192e2
purpose: scd2 implementation
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-incremental-loads-cdc-b74db18ed6"]
links: ["skill-dbt-project-structure-7397ed7111"]
---

## SCD2 Implementation

Use `effective_from` / `effective_to` / `is_current` columns.

**Reliable cross-platform pattern (two steps):**
1. Close changed rows (set `effective_to`, `is_current = 0`)
2. Insert new current versions

A single MERGE cannot do both UPDATE and INSERT from one source row without the nested INSERT-over-MERGE-OUTPUT trick.

**Options:**
- **dbt snapshots**: cleaner when Silver layer is dbt-managed
- **Manual MERGE**: more control (e.g., Spark Delta MERGE in lakehouse pipelines)

**Query patterns:**
- Current state: `WHERE is_current = 1`
- Historical: `WHERE order_date BETWEEN effective_from AND effective_to`
- Forgetting these joins duplicates fact rows

---
