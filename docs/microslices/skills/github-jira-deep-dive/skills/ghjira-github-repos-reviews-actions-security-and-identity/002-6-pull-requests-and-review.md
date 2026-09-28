---
id: skill-6-pull-requests-and-review-18849318f4
purpose: 6 pull requests and review
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: ["skill-5-repos-organizations-permissions-761f48cfaf"]
links: ["skill-7-rulesets-and-branch-protection-2993182716"]
---

## §6. Pull Requests and Review

**⚠️ The evidence on review is fairly consistent and mostly ignored:**
```
⚠️ SMALL PRs GET BETTER REVIEWS. Defect-finding drops sharply above a few
   hundred lines. ⚠️ Large PRs get "LGTM" — the review theatre outcome
⚠️ REVIEW LATENCY is usually the dominant term in cycle time (§24), not
   coding time. A PR waiting a day is a day of lead time
⚠️ AUTHORS should make review easy: a description of WHY, a self-review
   pass, and logically separated commits
```
**⚠️ Mechanics worth knowing**: **draft PRs; ⚠️ suggested changes (reviewers can propose
exact edits the author applies in one click — underused); review threads and resolution;
merge queue (⚠️ tests each PR against the state it will actually merge into, which
prevents the semantic conflicts that "green PR, broken main" comes from); auto-merge; and
required conversation resolution.**
**⚠️ Merge strategies**: ⚠️ **merge commit (preserves branch structure), squash (one commit
per PR — the cleanest main history and it discards intermediate commits), rebase-merge
(linear, no merge commit).** **⚠️ Pick one per repo and enforce it (§7); mixing them makes
history hard to reason about.**

---
