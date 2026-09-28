---
id: skill-dbt-project-structure-7397ed7111
purpose: dbt project structure
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-scd2-implementation-e91c9192e2"]
links: ["skill-orchestration-tool-selection-33376f13a6"]
---

## dbt Project Structure

Three-layer architecture:

| Layer | Description | Materialization | Rules |
|---|---|---|---|
| **Staging** | 1:1 with sources; rename/cast/basic categorization | Views | No joins; prefix `stg_` |
| **Intermediate** | Business logic, joins, re-graining | Ephemeral | Referenced by only one downstream (if more, make it a macro) |
| **Marts** | Wide/denormalized entities | Tables | ≤4–6 joins; prefix by domain |

**Materialization progression:** view → table (when query is slow) → incremental (only when table builds are too slow).

**Anti-patterns to avoid:**
- `finance_orders` vs `marketing_orders` — build one source of truth instead
- Splitting ML vs reporting marts
- Using seeds to load source data
- Using tags instead of folders as primary selectors

**dbt tests**: `not_null`, `unique`, `accepted_values`, `relationships` on every model. Using thresholds/severities to suppress failing tests hides anomalies and erodes audit trust.

---
