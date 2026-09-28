---
id: skill-25-anti-patterns-7f07f88840
purpose: 25 anti patterns
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-integration-metrics-and-anti-patterns/SKILL.md
requires: ["skill-24-metrics-088aa36fcd"]
links: []
---

## §25. Anti-Patterns

```
⚠️ Configuring the tool instead of deciding the process (§1)
⚠️ Editing a shared Jira scheme without checking what else uses it (§13)
⚠️ Creating a custom field instead of reusing one (§13, §22)
⚠️ Choosing team-managed/company-managed without knowing the difference (§14)
⚠️ Fifteen-status workflows nobody updates accurately (§15)
⚠️ status != Done instead of resolution = Unresolved (§16)
⚠️ Velocity as a cross-team or individual performance metric (§17, §24)
⚠️ Huge pull requests, then complaining review is superficial (§6)
⚠️ Long-lived feature branches, then blaming the merge tool (§3)
⚠️ Rebasing shared history; force-push without --force-with-lease (§3)
⚠️ pull_request_target with checkout of PR code (§8)
⚠️ Unpinned third-party actions (§8)
⚠️ Cleaning a leaked secret from history without rotating it first (§9)
⚠️ PATs for automation instead of a GitHub App (§11)
⚠️ Required status checks that never run on skipped paths (§7)
⚠️ Dependabot version updates left ungrouped until everyone ignores them (§9)
⚠️ Asking people to update both Jira and GitHub by hand (§23)
⚠️ Measuring individuals with DORA metrics (§24)
```
