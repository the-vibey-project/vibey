---
id: skill-13-observability-3dad571535
purpose: 13 observability
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-storage-databases-analytics-and-observability/SKILL.md
requires: ["skill-12-ai-ml-services-607931e3af"]
links: []
---

## §13. Observability

```
Metrics/logs   CloudWatch       Azure Monitor       Cloud Monitoring/Logging
Tracing        X-Ray            App Insights        Cloud Trace
Audit          ⚠️ CloudTrail     ⚠️ Activity Log      ⚠️ Cloud Audit Logs
```
**⚠️ The audit log is the one you must configure correctly and retain**: **CloudTrail,
Activity Log and Cloud Audit Logs are how you answer "who did this and when" after an
incident.** ⚠️ **Ensure they're enabled organization-wide, written to an account/project
the operators of the audited estate cannot modify, and retained long enough to matter.**
⚠️ **Data-plane logging (e.g. object-level reads) is usually OFF by default and is
frequently what you need.**
**⚠️ Native observability is adequate and expensive at volume** — **log ingestion and
retention charges are a common surprise line item, and this is why third-party
observability vendors exist.**
