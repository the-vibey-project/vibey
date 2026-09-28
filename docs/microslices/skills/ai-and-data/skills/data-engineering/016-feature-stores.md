---
id: skill-feature-stores-012d8cc2ed
purpose: feature stores
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-schema-evolution-data-contracts-3628ce5b27"]
links: ["skill-mlflow-production-patterns-be157f33f1"]
---

## Feature Stores

**Solve:** training-serving skew, online/offline consistency, feature reuse.

| Store | Type | Best for |
|---|---|---|
| **Feast** (Linux Foundation) | Open-source, bring-your-own-infra | Cost/flexibility/no lock-in; you own pipeline and writes to online store |
| **Tecton** (ex-Uber Michelangelo team) | Managed; includes transformation/compute | Mission-critical real-time; eliminates skew "by construction"; sub-10ms p99 online serving |

**Offline store**: BigQuery/Snowflake/S3 for point-in-time-correct training sets.
**Online store**: Redis/DynamoDB for low-latency inference.

Use Feast for flexibility; Tecton for managed SLAs on real-time use cases.

---
