---
id: skill-staged-implementation-roadmap-e9b8287e07
purpose: staged implementation roadmap
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/github-atlassian/SKILL.md
requires: ["skill-part-4-cross-cutting-concerns-a623125fdd"]
links: []
---

## Staged Implementation Roadmap

### Stage 1 — Stabilize Identity and Deprecation Exposure (Now)
1. **Migrate Bitbucket app passwords to API tokens/OIDC before June 9, 2026 brownouts** — this is the most urgent hard deadline
2. Audit Connect app dependencies; confirm vendors have Forge versions before Q4 2026
3. Standardize SSO/SCIM on one IdP feeding both ecosystems
4. Decide **EMU vs standard GHEC** using the OSS-contribution and data-residency tests

### Stage 2 — Modernize Governance (Next Quarter)
1. Migrate branch protection → **organization rulesets** in evaluate mode first, then enforce; add metadata rules for issue-keyed branch names
2. Enable **merge queue** on busy default branches (remember the `merge_group` trigger)
3. Scope **GHAS Secret Protection + Code Security** to active repos; turn on push protection org-wide with delegated bypass

### Stage 3 — Integrate and Measure (6–12 Months)
1. Deploy GitHub for Jira; replace smart-commit reliance with Actions-driven transitions
2. Stand up DORA metrics via a cross-platform tool
3. Pilot **Copilot coding agent / code review** and **Rovo agents** on contained workflows; set spend alerts

### Thresholds That Change the Plan
- Cross ~30 engineers or need workflow gates/portfolio reporting → move planning to Jira (not GitHub Projects)
- Active-committer count balloons with bots/contractors → re-scope GHAS repos to control cost
- Copilot agentic usage drives credit overages → cap org spend and restrict premium models
- Air-gapped/sovereign requirements → GHES + Bitbucket DC (until 2029)
