---
id: skill-comparison-bitbucket-vs-github-actions-vs-azure-devops-f249455729
purpose: comparison bitbucket vs github actions vs azure devops
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-pricing-may-2026-atlassian-list-c3a16ac651"]
links: ["skill-known-limitations-and-gotchas-eea0d53e7f"]
---

## Comparison: Bitbucket vs GitHub Actions vs Azure DevOps

| Feature | Bitbucket Pipelines | GitHub Actions | Azure DevOps |
|---|---|---|---|
| Pipeline structure | Single YAML file | Multiple workflow files | YAML + classic editor |
| Hosted OS | Linux only | Linux, Windows, macOS | Linux, Windows, macOS |
| OIDC to Azure | **Not supported** | Native (azure/login) | Native (workload identity) |
| Multi-approver gates | trigger: manual only | Environments + required reviewers | Approvals & Checks |
| Marketplace | 50–100+ pipes | 20,000+ actions | Thousands of extensions |
| Free build minutes/mo | 50 | 2,000 | 1,800 |
| Native secret scanning | No (third-party pipes) | Yes (GitHub Advanced Security) | No (third-party tasks) |
| Jira integration | Native | Via GitHub Issues | Via Azure Boards |
| Matrix builds | Manual parallel expansion | Native strategy.matrix | Via PowerShell loops |
| Job DAG | No (sequential + parallel) | Yes (needs:) | Yes (dependsOn) |

---
