---
id: skill-28-quick-reference-c4cc234a80
purpose: 28 quick reference
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-reference/SKILL.md
requires: ["skill-27-misconceptions-fcbc29e466"]
links: ["skill-29-method-bd313c886a"]
---

## §28. Quick Reference

### 28.1 Picker
| Question | Where |
|---|---|
| I broke my repo | ⚠️ **`git reflog` first, always** (§4 → `ghjira-git-data-model-branching-and-recovery`) |
| Merge or rebase? | ⚠️ **Rebase your unpushed work; merge shared branches** (§3 → `ghjira-git-data-model-branching-and-recovery`) |
| Undo a commit others have pulled | ⚠️ **`git revert`, not reset** (§4 → `ghjira-git-data-model-branching-and-recovery`) |
| Reviews are superficial | ⚠️ **The PRs are too big** (§6 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| PR stuck on a check that never runs | ⚠️ **Path filter + required check** (§7 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Automating against GitHub | ⚠️ **GitHub App, not a PAT** (§11 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Secret got committed | ⚠️ **ROTATE it, then clean history** (§9 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Enforcing policy across many repos | ⚠️ **Org-level rulesets** (§7 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| New Jira project — which type? | ⚠️ **§14 → `ghjira-jira-configuration-workflows-and-jql`, and decide deliberately** |
| Need a new Jira field | ⚠️ **Check whether one exists first** (§13 → `ghjira-jira-configuration-workflows-and-jql`, §22 → `ghjira-jira-boards-automation-permissions-and-hygiene`) |
| Editing a Jira workflow | ⚠️ **Check what else uses the scheme** (§13 → `ghjira-jira-configuration-workflows-and-jql`) |
| Find my open work | ⚠️ **`assignee = currentUser() AND resolution = Unresolved`** (§16 → `ghjira-jira-configuration-workflows-and-jql`) |
| What's been stuck? | ⚠️ **`status WAS "Blocked" DURING (-30d, now())`** (§16 → `ghjira-jira-configuration-workflows-and-jql`) |
| People forget to update tickets | ⚠️ **Automation, not reminders** (§19 → `ghjira-jira-boards-automation-permissions-and-hygiene`) |
| Which is source of truth for status? | ⚠️ **Pick one; automate the other** (§23 → `ghjira-integration-metrics-and-anti-patterns`) |
| What should we measure? | ⚠️ **DORA + cycle time. Never individuals** (§24 → `ghjira-integration-metrics-and-anti-patterns`) |
| Self-managed Atlassian, what now? | ⚠️ **§26.1's dates. This is a project** |

### 28.2 Setup checklist for a new repo
- [ ] ⚠️ **Ruleset on the default branch: PR required, checks required, no force push** (§7 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] CODEOWNERS, and owner review required rather than requested (§5 → `ghjira-github-repos-reviews-actions-security-and-identity`, §7 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] ⚠️ **One merge strategy chosen and enforced** (§6 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] ⚠️ **`permissions:` set explicitly in workflows; actions pinned to SHA** (§8 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] ⚠️ **Secret scanning with PUSH PROTECTION enabled** (§9 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] Dependabot on, version updates grouped (§9 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] ⚠️ **OIDC to cloud providers rather than stored credentials** (§8 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] Concurrency groups to cancel superseded runs (§8 → `ghjira-github-repos-reviews-actions-security-and-identity`)
- [ ] ⚠️ **Issue key convention enforced by check, not by reminder** (§23 → `ghjira-integration-metrics-and-anti-patterns`)

---
