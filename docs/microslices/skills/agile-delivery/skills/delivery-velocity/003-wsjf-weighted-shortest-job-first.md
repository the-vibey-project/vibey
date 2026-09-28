---
id: skill-wsjf-weighted-shortest-job-first-7d77493bd3
purpose: wsjf weighted shortest job first
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-ruthless-scope-reduction-e1adb5cc3e"]
links: ["skill-little-s-law-and-wip-limits-4810acb33c"]
---

## WSJF: Weighted Shortest Job First

WSJF (from Don Reinertsen's *The Principles of Product Development Flow*) provides the economic framework for prioritization and scope decisions.

### Formula
```
WSJF = Cost of Delay / Job Duration (size)
```

Higher WSJF = do this first. WSJF naturally favors high-value, short-duration work and penalizes bloated scope.

### Cost of Delay Components
Cost of Delay = User/Business Value + Time Criticality + Risk Reduction/Opportunity Enablement

Score each on a relative scale (1, 2, 3, 5, 8, 13) using the Fibonacci sequence. Sum the three components, then divide by job size.

### Why WSJF Matters
- **85% of product managers cannot quantify their Cost of Delay** (Reinertsen)
- Intuitive estimates of Cost of Delay differ by **50:1 across team members** without explicit discussion
- Making Cost of Delay explicit transforms prioritization from opinion-driven to evidence-driven
- WSJF prevents the common mistake of sequencing large, low-value items over small, high-value ones

### Practical Application
| Feature | Value | Time Crit. | Risk/Opp. | CoD | Size | WSJF |
|---|---|---|---|---|---|---|
| Login SSO | 13 | 8 | 5 | 26 | 3 | **8.7** |
| Dashboard export | 5 | 2 | 1 | 8 | 5 | 1.6 |
| Audit log | 8 | 13 | 8 | 29 | 8 | 3.6 |

Do Login SSO first (highest WSJF), then Audit log, then Dashboard export.

---
