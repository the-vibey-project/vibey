---
id: skill-9-operations-and-observability-097f9fa372
purpose: 9 operations and observability
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-cost-security-and-operations/SKILL.md
requires: ["skill-8-security-and-shared-responsibility-2efeb1bbef"]
links: []
---

## §9. Operations and Observability

**[DURABLE] The three signals plus two**: metrics, logs, traces — and **profiles** and
**events** are increasingly treated as first-class.

**[VERSIONED] OpenTelemetry is the vendor-neutral standard** and the right default for
instrumentation, precisely because it decouples your instrumentation from your backend
choice — which is a lock-in decision you'd rather not make twice.

**What to actually measure**: **SLIs and SLOs** derived from user-visible behaviour, with
**error budgets** driving the release-vs-stability conversation; the **RED method**
(Rate, Errors, Duration) for services; **USE** (Utilization, Saturation, Errors) for
resources; and **⚠️ the four golden signals** — latency, traffic, errors, saturation.

**⚠️ Alert on symptoms, not causes.** Alert on "users are seeing errors," not "CPU is at
80%." **Every alert should be actionable and should map to a runbook** — alert fatigue is
a reliability problem, not an annoyance.

**Also**: distributed tracing (⚠️ **essential once you have more than a handful of
services**), structured logging with correlation IDs, **synthetic monitoring** (⚠️ **you
want to know before your users tell you**), **status-page and provider-health integration
into your own alerting** (a 2025 lesson — §6 → `cloud-architecture-and-resilience`), and **cost as an observability signal**
(§7).
