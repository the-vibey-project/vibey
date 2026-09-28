---
id: skill-pricing-may-2026-atlassian-list-c3a16ac651
purpose: pricing may 2026 atlassian list
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-runners-hosted-vs-self-hosted-e79a3588ad"]
links: ["skill-comparison-bitbucket-vs-github-actions-vs-azure-devops-f249455729"]
---

## Pricing (May 2026, Atlassian List)

| Plan | Price | Build minutes/mo | Concurrent steps | Key features |
|---|---|---|---|---|
| **Free** | $0 (≤5 users) | 50 | 10 | Unlimited repos, basic CI/CD |
| **Standard** | $3.65/user/mo (flat $18.25/mo for 1–5) | 2,500 | up to 600 | 4x/8x step sizes |
| **Premium** | $7.25/user/mo (flat $36.25/mo for 1–5) | 3,500 | up to 600 | IP allowlisting, merge checks, deployment permissions, required 2SV |

- Overage: $10 per 1,000 additional minutes
- Additional LFS storage: $10 per 100 GB
- Build minutes are **workspace-pooled** — a single noisy repo can starve all others. No per-repo quota.

**SSO is a separate Atlassian Guard subscription**: Guard Standard $4.20/user/mo, Guard Premium $8.18/user/mo. For 100-user enterprise on Premium + Guard Premium: effective $15.43/user/month, not $7.25.

**Cost intuition:** A 16-minute pipeline fanning out across 4 parallel containers can easily consume 70+ workspace minutes per run. 100 runs/day = ~210,000 minutes/month = ~$2,100/month in overage above the Standard plan's 2,500 bundled minutes.

---
