---
id: skill-24-metrics-088aa36fcd
purpose: 24 metrics
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-integration-metrics-and-anti-patterns/SKILL.md
requires: ["skill-23-integrating-github-and-jira-1474eb96e8"]
links: ["skill-25-anti-patterns-7f07f88840"]
---

## §24. ⚠️ Metrics

**⚠️ DORA's four keys are the best-validated delivery metrics available:**
```
⚠️ DEPLOYMENT FREQUENCY · LEAD TIME FOR CHANGES  (throughput)
⚠️ CHANGE FAILURE RATE · TIME TO RESTORE SERVICE (stability)
⚠️ Later work adds RELIABILITY as a fifth
```
⚠️ **The key research finding is that throughput and stability are NOT a tradeoff** —
**high performers do better on both, which refutes the "move fast and break things vs move
slow and be safe" framing.**
> **⚠️ GOTCHA — DORA metrics are TEAM diagnostics, not individual performance measures,
> and using them for the latter destroys them.** ⚠️ **Anything measured in Jira or GitHub
> can be gamed: commit counts reward churn, lines changed reward verbosity, story points
> inflate, ticket counts reward splitting.** **⚠️ Goodhart's law is unusually fast here
> because the measurement is fully under the measured party's control.**
> **⚠️ Never measure individuals with these systems.** **Use them to find where WORK gets
> stuck.**

**⚠️ Flow metrics worth watching instead of output counts**: **cycle time distribution
(⚠️ the 85th percentile is more useful than the mean for forecasting), WIP, flow
efficiency (⚠️ active time ÷ total elapsed — typically shockingly low, often under 20%,
and that gap IS the improvement opportunity), and blocked time.**
**⚠️ The single most actionable thing in most teams is PR review latency** (§6 → `ghjira-github-repos-reviews-actions-security-and-identity`) —
**it's measurable, it's usually large, and it's fixable by agreement rather than tooling.**

---
