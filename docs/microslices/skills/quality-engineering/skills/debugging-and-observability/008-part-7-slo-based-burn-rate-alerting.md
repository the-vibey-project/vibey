---
id: skill-part-7-slo-based-burn-rate-alerting-040b76deff
purpose: part 7 slo based burn rate alerting
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-6-ebpf-for-production-debugging-02daf74bfc"]
links: ["skill-part-8-error-handling-design-and-patterns-8d895d7b4d"]
---

## Part 7 — SLO-Based Burn-Rate Alerting

**The core tension:** too few alerts miss problems; too many cause alert fatigue. The SRE philosophy is **symptom-based alerting** on user-visible behavior, not cause-based alerting.

### SLO-Based Multi-Window Burn-Rate Alerting (Google SRE Workbook, Ch. 5)

**Burn rate** = how fast you consume the error budget relative to the rate that would exactly exhaust it over the SLO window.

**Recommended multi-window, multi-burn-rate setup (30-day SLO window):**

| Trigger | Burn Rate | Long Window | Short Window | Action |
|---------|-----------|-------------|--------------|--------|
| Page immediately | ~14.4 | 1 hour | 5 min | 2% budget consumed |
| Ticket | ~6 | 6 hours | 30 min | 5% budget consumed |
| Track | ~1 | 3 days | 6 hours | 10% budget consumed |

The short secondary window (1/12 of the long window) reduces false positives.

**Example threshold:** If your error rate is fine but burn rate exceeds ~14.4 on a 1-hour window, page immediately; if a 1% error rate sits on a 99.9% SLO, that's a 10× burn — treat it as an active incident.

ML-based anomaly detection (Datadog Watchdog, Dynatrace Davis) supplements static thresholds.

**OpsGenie sunset notice:** End of sale June 4, 2025; full end of support April 5, 2027, after which all OpsGenie data is deleted. Migrate to PagerDuty, incident.io, Jira Service Management, or Compass.

---
