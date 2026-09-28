---
id: skill-recommendations-by-team-profile-36d40bd4e5
purpose: recommendations by team profile
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-security-scanning-integration-3b88587eb7"]
links: []
---

## Recommendations by Team Profile

**Azure shop committed to Atlassian ecosystem:**
Use Bitbucket Pipelines for CI, store Azure credentials as deployment-scoped secured variables, automate rotation, enforce Premium deployment permissions to restrict who can deploy to production.

**Security review demands zero long-lived secrets:**
Build the Azure Function token broker (Option B above). 1 engineering-week to build, negligible runtime cost. Treats the function as security-critical with rate limiting and Sentinel logging.

**Large enterprise with .NET + Azure portfolio:**
Hybrid: Bitbucket as code host, Azure Pipelines YAML pipelines for deployment legs (workload-identity service connections, native Windows/macOS hosted agents). One Azure DevOps Basic license per active user cleanly resolves the OIDC gap and hosted runner limitations.

**Migration trigger thresholds:**
- If monthly Bitbucket overage minutes bill exceeds ~$1,500, model GitHub Actions or Azure Pipelines economics
- If maintaining more than 10 self-hosted runners, evaluate the Premium Runners tier or GitHub's larger hosted runners
- If BCLOUD-22206 ships native Azure OIDC, retire the token broker immediately
