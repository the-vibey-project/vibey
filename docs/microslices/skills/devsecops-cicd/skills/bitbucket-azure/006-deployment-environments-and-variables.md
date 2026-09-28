---
id: skill-deployment-environments-and-variables-d0485c9322
purpose: deployment environments and variables
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-azure-pipes-reference-dfda999f50"]
links: ["skill-yaml-anchors-for-in-repo-reuse-8cab47e16f"]
---

## Deployment Environments and Variables

Bitbucket has three variable scopes:
1. **Workspace variables** — shared across all repos in the workspace
2. **Repository variables** — scoped to one repo
3. **Deployment variables** — scoped to a specific environment (`deployment: production`)

Use deployment variables for environment-specific credentials. Variables marked **Secured** are masked in logs and not accessible via the API after creation.

**Important:** The only built-in gate is `trigger: manual` — any user with write access can trigger. There is no native multi-approver workflow, no required reviewers, no environment protection rules equivalent to GitHub Environments or Azure DevOps Approvals & Checks.

On **Premium** plan, deployment permissions allow restricting which users can deploy to each environment. For multi-approver workflows, integrate Jira Service Management change management.

---
