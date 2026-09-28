---
id: skill-12-access-control-ee3beb9a79
purpose: 12 access control
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-access-control-embedded-and-testing/SKILL.md
requires: []
links: ["skill-13-embedded-analytics-a55dbe1fb9"]
---

## §12. Access Control

**Row-level security** (⚠️ **a manager sees only their region — and the rule must be
enforced in the semantic or database layer, not in a dashboard filter, which is trivially
bypassed**), **column-level masking** for PII, **object-level** permissions.
**⚠️ The aggregation leak is the subtle one**: **someone with no row access to salaries but
access to averages can often infer individual values from a small enough group.**
**Minimum-group-size thresholds exist for this reason.**
**⚠️ And embedded analytics multiplies the risk** — **a tenant filter applied client-side
is not access control** (§13).

---
