---
id: skill-staged-implementation-roadmap-a978d36de3
purpose: staged implementation roadmap
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-iac-in-pipelines-3b733bb3b9"]
links: []
---

## Staged Implementation Roadmap

### Stage 0 — Eliminate Static Credentials (Weeks, Not Months)
Migrate every CI→cloud connection to OIDC. **Hard deadline: Bitbucket app-password integrations must move before June 9, 2026.**

Benchmark: if any pipeline still reads a long-lived cloud secret from CI, you are not done.

### Stage 1 — Delivery Fundamentals
- Trunk-based development + feature flags
- Small PRs + required status checks + merge queue
- Build once, promote immutable artifacts by git SHA
- Fail-fast pipeline ordering
- Instrument all five DORA metrics (including rework rate)

Threshold: if median PR lifetime exceeds a few days or you rebuild artifacts per environment, fix this before investing in advanced tooling.

### Stage 2 — Supply-Chain Security
- Generate SBOMs (Syft or CycloneDX build plugins)
- Scan with Trivy or Grype (pin and verify scanner versions)
- Sign images keyless with Cosign
- Emit SLSA provenance (target L2→L3)
- Prioritize by EPSS/KEV, not CVSS volume

### Stage 3 — Progressive Delivery and GitOps
- Argo CD (UI + RBAC) or Flux (lightweight, multi-cluster)
- Argo Rollouts (Argo shops) or Flagger (Flux shops)
- Always gate on success-rate AND latency; automated rollback
- Azure PaaS: Container Apps revisions or App Service slots

### Stage 4 — Platform Engineering and AI
- Encode best practices as opt-in golden paths — never mandates
- Commercial IDP for fast ROI; Backstage only with ≥3–5 dedicated engineers
- AI code review as quality gate; predictive test selection to control CI cost

### Startup vs Enterprise Calibration
- **Startups (1–3 teams):** GitHub Actions or GitLab SaaS, hosted runners, GitHub Flow, OIDC, Trivy + Cosign, App Service/Container Apps slots — skip Backstage and Bazel
- **Enterprise (10+ teams, 100+ services):** self-hosted ephemeral runners (ARC), org-wide golden-path templates + policy-as-code, Argo CD/Flux multi-cluster GitOps, an IDP, DORA-metrics tooling (LinearB/Sleuth/Faros/Jellyfish)
