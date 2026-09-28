---
id: skill-13-embedded-analytics-a55dbe1fb9
purpose: 13 embedded analytics
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-access-control-embedded-and-testing/SKILL.md
requires: ["skill-12-access-control-ee3beb9a79"]
links: ["skill-14-testing-analytics-b1dc9113f1"]
---

## §13. Embedded Analytics

**⚠️ Multi-tenancy is the whole problem.** **A tenant filter must be enforced server-side
from a signed token, never from a client-supplied parameter.**
**Approaches**: **iframe with a signed URL** (simple, limited styling), **SDK/JS
embedding**, ⚠️ **or headless/API — query a semantic layer and render in your own UI,
which gives full control and the most work** (§5 → `reporting-semantic-layer-time-and-performance`, §16.1 → `reporting-reference`).
**⚠️ Practical concerns**: per-tenant performance isolation (⚠️ **one large tenant should
not degrade everyone**), white-labelling, and **caching correctly per tenant — a cache key
that omits tenant identity is a data breach.**

---
