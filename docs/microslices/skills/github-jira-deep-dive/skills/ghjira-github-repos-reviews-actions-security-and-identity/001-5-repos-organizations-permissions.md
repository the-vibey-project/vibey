---
id: skill-5-repos-organizations-permissions-761f48cfaf
purpose: 5 repos organizations permissions
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: []
links: ["skill-6-pull-requests-and-review-18849318f4"]
---

## §5. Repos, Organizations, Permissions

```
ACCOUNT TYPES   personal · organization · ⚠️ enterprise (a container of orgs)
REPO ROLES      Read · Triage · Write · Maintain · Admin
⚠️ TEAMS        nested teams inherit permissions DOWNWARD.
   ⚠️ Permissions are the UNION of everything granted — there is no deny
CODEOWNERS      ⚠️ auto-request reviews by path; combine with rulesets (§7)
   to make owner review REQUIRED rather than merely requested
```
**⚠️ The permission model is additive, which surprises people coming from systems with
deny rules** — ⚠️ **you cannot subtract access by adding a team; you remove the grant that
provides it.**
**⚠️ Monorepo vs polyrepo**: ⚠️ **monorepo simplifies cross-cutting change, atomic commits
and shared tooling, at the cost of CI complexity and needing path filters and CODEOWNERS
to keep review sane.** **Polyrepo simplifies ownership and access at the cost of
coordinated change.** **⚠️ Neither is right generally; the deciding factor is how often
changes cross repository boundaries.**

---
