---
id: skill-platform-selection-1a8ec9df4f
purpose: platform selection
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-dora-metrics-the-evidence-base-ee785c9856"]
links: ["skill-branching-strategy-a377b868dd"]
---

## Platform Selection

### Decision Matrix

| Platform | Best For | Key Strength | Honest Weakness |
|---|---|---|---|
| **GitHub Actions** | Cloud-native, GitHub-centric teams | Ecosystem (20,000+ marketplace actions), OIDC, Environments | 6-hour job limit; third-party action supply-chain risk |
| **Azure DevOps** | Microsoft-stack enterprise | Most mature deployment-environment/approval model | Migrating GUI pipelines to YAML (do this now) |
| **GitLab CI** | All-in-one DevSecOps | SCM + CI + security + registry in one; CI/CD Catalog (GA) | Vendor lock-in risk |
| **Jenkins** | Air-gapped, maximum flexibility, existing investment | 1,800+ plugins, any VCS | Losing share; self-managed infra; dated UX; high TCO in DevOps engineer time |
| **Bitbucket Pipelines** | Atlassian/Jira shops | Native Jira integration, zero-config deployment tracking | **Hard deprecation deadline** (app passwords); fewer Actions minutes |

### Platform Deep-Dives

**GitHub Actions key capabilities:**
- **OIDC federation** (bind to Environments with required reviewers via `environment:<env>` subject, not just branches)
- **Environments** + deployment protection rules: required reviewers, wait timers, branch restrictions
- **Actions Runner Controller (ARC)** for Kubernetes autoscaling — use **ephemeral** runner pods (fresh pod per job, destroyed after — prevents state leakage)
- ARC 0.13.0 (Oct 2025): sidecar Docker-in-Docker (K8s 1.29+), automatic pod retries (up to 5), OpenShift support, Azure Key Vault secret retrieval (GA), `kubernetes-novolume` mode
- Security: pin third-party actions to commit SHAs; minimize `GITHUB_TOKEN` permissions; set explicit `permissions` blocks
- Reusable workflows (`workflow_call`) vs composite actions vs custom JS/Docker actions

**Azure DevOps Pipelines key capabilities:**
- **Workload Identity Federation (GA):** ARM service connections use federation subject (`sc://<org>/<project>/<connection>`) instead of a client secret; use the one-click Convert tool or bulk PowerShell for migration — treat as mandatory
- YAML multi-stage pipelines supersede classic GUI pipelines — migrate now
- Templates (step/job/stage/pipeline) for reuse; variable groups + Azure Key Vault integration
- **Pipeline decorators** inject mandatory org-wide steps (compliance-as-code)
- Environments: Kubernetes/VM resources, approval gates, deployment strategies (runOnce, rolling, canary, blue-green)

**GitLab CI key capabilities:**
- **CI/CD Components + Catalog (GA in 17.0, May 2024):** versioned, reusable, semver-tagged pipeline components (modern replacement for ad-hoc `include`; catalog hosts hundreds of components, limit raised to 100 per project in 18.5)
- Built-in SAST, DAST, dependency scanning, secret detection
- Review Apps for ephemeral per-MR environments
- Merge trains for keeping main green at scale

**Bitbucket Pipelines — URGENT:**
- **App-password hard deadline:** no new creation since Sept 9, 2025; brownouts start June 9, 2026; full removal July 28, 2026
- **Action required NOW:** migrate all Bitbucket CI integrations to API tokens with scopes or OIDC (`oidc: true`, `$BITBUCKET_STEP_OIDC_TOKEN`)
- Steps (`bitbucket-pipelines.yml`) + Pipes ecosystem + OIDC for cloud auth

**Jenkins honest assessment:**
- Market share estimated ~44% (large installed base) but actively losing share
- Use only for: air-gapped/on-prem/compliance-heavy, existing large Jenkins investments, multi-VCS shops, maximum-flexibility custom pipelines
- Use Declarative over Scripted pipelines; Shared Libraries for reuse; Kubernetes plugin for dynamic agents
- AI-assisted migration tooling (GitHub Actions Importer) now compresses Jenkins→Actions migrations from years to months

---
