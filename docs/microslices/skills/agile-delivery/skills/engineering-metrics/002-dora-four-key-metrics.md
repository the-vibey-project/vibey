---
id: skill-dora-four-key-metrics-ec7ec99d23
purpose: dora four key metrics
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-the-measurement-hierarchy-36362a6bb3"]
links: ["skill-space-framework-a9c5d7b5a3"]
---

## DORA Four Key Metrics

The four key DevOps metrics from the DORA research program measure two dimensions of software delivery: **throughput** (Deployment Frequency, Lead Time) and **stability** (Change Failure Rate, Recovery Time). Elite teams achieve high throughput *and* high stability simultaneously — they are not trade-offs.

### 2024 Benchmarks

| Metric | Elite | High | Medium | Low |
|---|---|---|---|---|
| **Deployment Frequency** | Multiple per day | Daily to weekly | Weekly to monthly | Monthly to 6 months |
| **Lead Time for Changes** | < 1 day | 1 day – 1 week | 1 week – 1 month | 1–6 months |
| **Change Failure Rate** | 0–5% | ~10% | ~15% | 16–30%+ |
| **Failed Deployment Recovery Time (FDRT)** | < 1 hour | < 1 day | < 1 day | 1 week – 1 month |

**Important nuances:**
- Performance tiers are derived via **cluster analysis from annual survey data** — they shift year to year, not fixed targets
- DORA renamed MTTR to **"Failed Deployment Recovery Time" (FDRT)** and added **Reliability** as a fifth metric
- 19% of respondents reached Elite, 22% High in the 2024 survey
- The 2024 report found AI tools boost individual productivity but correlate with **worsened** software delivery performance at the team level — second consecutive year of this finding

### Metric Definitions

**Deployment Frequency (DF)**
How often code is successfully deployed to production (or released to end users). This is a proxy for batch size — teams that deploy multiple times per day are shipping small, low-risk changes continuously.

- Elite teams deploy **208–973× more frequently** than low performers
- Measure: pipeline run data; count successful production deployments per time period

**Lead Time for Changes (LT)**
Time from a code commit being made to that code being successfully running in production. Measures the speed of your delivery pipeline end-to-end.

- Measure: commit timestamp → production deployment timestamp
- Most CI/CD tools (Azure DevOps, GitHub Actions) can compute this via commit-to-release linking
- Long lead times indicate bottlenecks in review, testing, or deployment processes

**Change Failure Rate (CFR)**
Percentage of deployments that result in degraded service or require remediation (rollback, hotfix, forward-fix). Lower is better; elite teams have < 5% of deployments causing incidents.

- Measure: tag failed deployments in release pipelines; `(failed deployments / total deployments) × 100`
- Important: this measures deployments that caused incidents, not deployments that were technically successful

**Failed Deployment Recovery Time (FDRT)**
How quickly a team can restore service when a deployment causes an incident. Measures resilience and operational capability.

- Previously called MTTR (Mean Time to Recover/Restore)
- Measure: incident creation timestamp → incident resolution timestamp, filtered to incidents caused by deployments
- Elite < 1 hour requires robust monitoring, clear runbooks, and practiced incident response

### Instrumenting DORA in Azure DevOps

```
Deployment Frequency:
  - Query: release pipeline runs to Production environment
  - Automate: Azure DevOps Analytics → custom widget or Power BI report
  - Tag each release with deployment date

Lead Time:
  - Requires commit-to-production timestamp linking
  - Use AB#<WorkItemID> references in commits to link work items to PRs to builds to releases
  - Azure DevOps automatically creates these links when conventions are followed
  - Report: average time from first commit in work item to production deployment

Change Failure Rate:
  - Tag failed deployments in release pipeline with a "FAILED" custom field
  - Calculate: COUNT(failed) / COUNT(total) per time window
  - Include both rollbacks and hotfixes in "failed" count

FDRT:
  - Requires integration with incident tracking (Azure DevOps, ServiceNow, PagerDuty)
  - Measure: incident.created_at to incident.resolved_at for incidents tagged deployment-related
  - Filter to P1/P2 incidents only for meaningful data
```

### DORA and CABs

A critical DORA finding: **External approval processes (CABs) are negatively correlated with all four DORA metrics and have zero correlation with change failure rate.** Teams with formal external CAB processes were 2.6× more likely to be low performers. Peer review during development + automated deployment gates outperforms human approval gates on both velocity and stability.

---
