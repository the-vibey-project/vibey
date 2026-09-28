---
id: skill-gitops-and-progressive-delivery-kubernetes-standard-bbc74c9386
purpose: gitops and progressive delivery kubernetes standard
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-security-the-highest-leverage-action-d281b75233"]
links: ["skill-pipeline-architecture-principles-0492ed9816"]
---

## GitOps and Progressive Delivery (Kubernetes Standard)

### Argo CD vs Flux CD

Both are CNCF-graduated and excellent.

| | Argo CD | Flux CD |
|---|---|---|
| **Wins on** | Developer UX, rich web UI, SSO/RBAC, multi-cluster visibility, fast onboarding | Kubernetes-native modularity, lightweight footprint, native OCI/SOPS, air-gapped, 100% pull-based |
| **Favored by** | Teams where non-engineers (PMs, compliance) need sync status visibility | Platform teams building reproducible multi-cluster infrastructure |
| **Shorthand** | "Argo CD is for humans" | "Flux is for robots" |

### Argo Rollouts vs Flagger (Progressive Delivery)

| | Argo Rollouts | Flagger |
|---|---|---|
| **Model** | Replaces Deployment with `Rollout` CRD; explicit step-based control + UI | Wraps existing Deployments with zero manifest changes; automated canary lifecycle |
| **Metric providers** | More native providers (Prometheus, Datadog, New Relic, CloudWatch, Wavefront, Graphite) | Fewer native; same core function |
| **Natural pairing** | Argo CD teams | Flux teams |
| **Patterns supported** | Canary, blue-green, A/B, automated rollback | Same |

**Always define both success-rate AND latency thresholds** — error rate alone misses performance regressions.

### Azure PaaS Deployment Patterns

**Azure Container Apps (cleanest pattern):**
- Blue-green/canary via revisions + traffic weights + revision labels
- Set `activeRevisionsMode: multiple`
- Each revision gets its own FQDN for testing before taking traffic
- Rollback: `az containerapp ingress traffic set --label-weight blue=100 green=0`
- Revisions are immutable; standby revision scales to zero (no extra cost on Consumption)

**App Service:** deployment slots with warm-up health checks; mark env-specific config as slot-sticky.

**Azure Container Apps Jobs** can host self-hosted CI runners.

---
