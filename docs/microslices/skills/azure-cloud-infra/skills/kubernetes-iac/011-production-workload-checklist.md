---
id: skill-production-workload-checklist-0c887abb40
purpose: production workload checklist
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-environment-promotion-pattern-176e8946c7"]
links: ["skill-secret-management-options-334c62ddae"]
---

## Production Workload Checklist

Every production Deployment should have:

- Minimum 3 replicas
- PodDisruptionBudget with `maxUnavailable: 1` (never `maxUnavailable: 0` — blocks cluster upgrades)
- HPA with stabilization windows to prevent flapping
- Topology spread across zones (`DoNotSchedule`) and nodes (`ScheduleAnyway`)
- All three probe types: startup (`failureThreshold: 60`, slow start tolerance), liveness (lightweight self-check only, never check external deps), readiness (checks dependencies, removes from Service endpoints)
- Resource requests always set; memory limits always set; CPU limits not set (causes CFS throttling)
- Non-root user, readOnlyRootFilesystem, no privilege escalation, drop ALL capabilities
- Dedicated ServiceAccount with `automountServiceAccountToken: false`
- ServiceMonitor for Prometheus scraping
- Distroless or Chainguard base images (no shell, no package manager)
- Images pinned by digest, not tag: `myapp@sha256:abc123...`

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    memory: "256Mi"    # Always set memory limit
    # No CPU limit — allow bursting to avoid CFS throttling
```

---
