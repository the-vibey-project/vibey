---
id: skill-7-rulesets-and-branch-protection-2993182716
purpose: 7 rulesets and branch protection
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: ["skill-6-pull-requests-and-review-18849318f4"]
links: ["skill-8-github-actions-0124609904"]
---

## §7. Rulesets and Branch Protection

**⚠️ Rulesets are the modern replacement for classic branch protection**, ⚠️ **and the
practical advantages are layering (multiple rulesets apply together), pattern-based
targeting across many branches or tags, fine-grained bypass, and org-level application
across repos.**
```
COMMON RULES  require PR before merge · require N approvals ·
   ⚠️ dismiss stale approvals on new commits · require review from
   CODE OWNERS · require status checks to pass · require linear history ·
   require signed commits · ⚠️ block force pushes · restrict deletions
   ⚠️ require deployments to succeed · require merge queue
```
> **⚠️ GOTCHA — required status checks only work if the check actually RUNS.** ⚠️ **If a
> workflow is skipped by a path filter, the required check never reports, and the PR
> blocks forever waiting for something that will never arrive.** **⚠️ The fix is a
> "always-run" job that reports success for skipped paths, or careful use of
> `paths-ignore` semantics.** **This bites nearly every team that adopts path filters.**

**⚠️ Bypass lists are where governance quietly leaks** — ⚠️ **an admin bypass or an app
with bypass permission means the rule is advisory for that actor.** **Audit them.**
**⚠️ GitHub now offers automatic conversion of classic branch protection rules into
rulesets** (§26.2 → `ghjira-reference`), **which removes the main friction in migrating.**

---
