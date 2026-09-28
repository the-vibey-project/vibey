---
id: skill-part-1-github-1f7789b953
purpose: part 1 github
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/github-atlassian/SKILL.md
requires: ["skill-the-three-things-you-must-plan-around-now-e600ca920b"]
links: ["skill-part-2-atlassian-cc9b251323"]
---

## Part 1 — GitHub

### 1.1 Repositories and Governance

**Rulesets have superseded branch protection** as the model of choice:
- Multiple rulesets **aggregate** (most restrictive applies) vs branch protection (one rule "wins" by priority)
- Can be set at the **organization level** (GitHub Enterprise)
- Target branch-name patterns and tags
- Run in **evaluate (dry-run) mode** before enforcement
- Enforce **metadata rules** (commit message, branch naming, author email) natively — eliminating pre-receive hooks
- Branch protection still exists and layers with rulesets

**Three repository visibilities:**
- Public, private, and **internal** (enterprise accounts only) — internal = visible to all enterprise members, ideal for InnerSource

**CODEOWNERS:** routes review by path (last matching pattern wins); can be required via rulesets.

**GitHub merge queue (GA 2023):**
- Builds speculative merge commits (base + PRs ahead + this PR) and merges FIFO once required checks pass
- Requires the `merge_group` workflow trigger — **the single most common misconfiguration**
- Does not support wildcard branch patterns
- Designed and tested at scale (GitHub.com: 30,000+ PRs, 4.5M CI runs before GA)

### 1.2 Issues and Projects

**YAML issue forms** have largely superseded markdown templates for serious intake — structured dropdowns/checkboxes/validations.

**GitHub Issues vs Jira decision:**
- GitHub Issues + Projects: free, markdown-native, zero context-switch — sufficient for teams under ~20–30 developers
- Jira wins on: workflow enforcement (conditions/validators/post-functions), velocity/burndown/CFD reporting, cross-project portfolio visibility, issue hierarchy (Initiative→Epic→Story→Sub-task), 5,000+ Marketplace

**GitHub Projects (v2) honest gaps vs Jira:**
- No native velocity/cycle-time analytics
- Flat hierarchy (no true epics/parent-child without task-list workarounds)
- Limited fine-grained permissions ("QA can only move to Done" isn't expressible)
- Managed via GraphQL API

### 1.3 GitHub Actions

**Core building blocks:** triggers, matrix builds, concurrency controls, reusable workflows (`workflow_call`) vs composite/JS/Docker actions.

**Security and scale features:**
- **OIDC federation:** bind to Environments (`environment:<env>` subject) with required reviewers, not just branches — the right way to gate production
- **Environments + deployment protection rules:** required reviewers, wait timers, branch restrictions
- **Actions Runner Controller (ARC):** Kubernetes-native autoscaling using **ephemeral** runner pods (fresh pod per job, destroyed after — prevents state leakage and ensures no job is assigned to a shutting-down runner)
  - ARC 0.14.0 (March 2026): moved to `actions/scaleset` library client
  - Earlier releases added: native sidecar DinD, automatic pod retries (up to 5), OpenShift support, Azure Key Vault secret retrieval (GA), dual-stack IPv4/IPv6

**Security best practices:**
- Pin third-party actions to commit SHAs (Dependabot updates them)
- Minimize `GITHUB_TOKEN` permissions; set explicit `permissions` blocks
- Marketplace actions introduce third-party supply-chain risk

**Repository secrets/variables scope:** org, repo, and environment levels.

### 1.4 GitHub Advanced Security (GHAS) — Repriced April 1, 2025

GHAS was unbundled into two metered, committer-priced SKUs available even on Team:

| SKU | Price | Includes |
|---|---|---|
| **Secret Protection** | $19/active committer/mo | Push protection, validity checks, AI-detected generic secrets, 200+ partner patterns |
| **Code Security** | $30/active committer/mo | CodeQL code scanning, Copilot Autofix, security campaigns, dependency review |

**Active committer definition:** unique active committers on a 90-day window over repos where the feature is enabled.

**Cost control:** scope to specific repos — org-wide enablement counts every contractor and bot that pushes.

**Copilot Autofix:** covers 90%+ of alert types in JS/TS/Java/Python; suggestions remediate 2/3+ of found vulnerabilities.

**Other security features:**
- Dependabot: alerts, security updates, version updates, grouped updates via `dependabot.yml`
- Secret scanning push protection: blocks at push; delegated bypass (approval workflow); validity checks against provider APIs
- Custom patterns (up to 500/org via Hyperscan regex)
- **Artifact attestations** (GA June 2024): `actions/attest-build-provenance` via Sigstore → SLSA Build Level 2 out of the box, Level 3 with reusable workflows; no key management; Kubernetes admission controller for enforcement
- Security campaigns (2025): org-level security debt remediation workflows

### 1.5 GitHub Copilot

**The product is now a family of agents:**

| Feature | Status | Notes |
|---|---|---|
| Code completions | GA | Unlimited and unbilled on paid plans |
| Copilot Chat (IDE + GitHub.com) | GA | PR summaries, repo Q&A, slash commands, `@workspace` |
| Copilot code review | GA (April 4, 2025) | Automatic (via rules) + on-demand; 1M+ devs in first month of preview |
| Copilot coding agent | GA (Sept 25, 2025) | Assign issue → opens draft PR via GitHub Actions |
| Copilot CLI | GA | — |
| Agent mode (VS Code, JetBrains) | GA by early 2026 | Multi-file/multi-step agentic sessions |

**Billing changed June 1, 2026 to usage-based AI Credits (1 credit = $0.01, priced by token/model):**

| Plan | Price | AI Credits included |
|---|---|---|
| Business | $19/user/mo | $19 credits |
| Enterprise | $39/user/mo | $39 credits (also requires GHEC ~$21/user → real cost ~$60/user) |

- Code completions remain unlimited and unbilled
- **Copilot code review additionally consumes GitHub Actions minutes on private repos starting June 1, 2026** (public repos remain free)
- Agentic sessions can consume credits and Actions minutes quickly — set spend alerts

**Honest assessment:** measurably helps on boilerplate, tests, and low-to-medium-complexity well-tested codebases; underdelivers on novel architecture and large unfamiliar codebases.

### 1.6 Enterprise Identity (EMU)

**True SCIM provisioning requires GitHub Enterprise Cloud with Enterprise Managed Users (EMU).**
- Standard GHEC: only SCIM-triggered invitations (not full provisioning)
- **EMU hard tradeoff:** managed users cannot contribute to public repos or external OSS
- Okta + Entra split-IdP combination is explicitly unsupported
- **Data residency (GHE.com) requires EMU**

**GitHub Enterprise options:**
- **GHEC:** cloud-hosted, EMU optional, GitHub Connect bridge
- **GHES:** self-hosted HA (primary-replica, backup-utils), GitHub Connect bridge to GHEC; air-gapped option

### 1.7 Packages and Ecosystem

**GHCR** for GitHub-native flows; choose **Azure Artifacts/Artifactory** for polyglot enterprise artifact governance.

**GitHub Apps vs OAuth Apps vs PATs vs Actions tokens:**
- GitHub Apps (JWT→installation tokens): the right credential for automation
- PATs: simpler but coarser; fine-grained PATs now available
- Actions `GITHUB_TOKEN`: repo-scoped, short-lived — prefer over PATs in Actions workflows

**Codespaces:** devcontainers + prebuilds; billed per compute-hour.

---
