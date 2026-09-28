---
id: skill-27-misconceptions-fcbc29e466
purpose: 27 misconceptions
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-reference/SKILL.md
requires: ["skill-26-what-s-live-verified-august-2026-478ba2553c"]
links: ["skill-28-quick-reference-c4cc234a80"]
---

## §27. Misconceptions

| Misconception | Correction |
|---|---|
| Git commits store diffs | ⚠️ **They store snapshots; diffs are computed** (§2 → `ghjira-git-data-model-branching-and-recovery`) |
| A branch contains commits | ⚠️ **It's a pointer. Deleting it loses nothing** (§2 → `ghjira-git-data-model-branching-and-recovery`, §4 → `ghjira-git-data-model-branching-and-recovery`) |
| Deleting a branch loses the work | ⚠️ **Reflog. Committed work is hard to lose** (§4 → `ghjira-git-data-model-branching-and-recovery`) |
| Rebase is just a tidier merge | ⚠️ **It rewrites hashes. Never on shared history** (§3 → `ghjira-git-data-model-branching-and-recovery`) |
| `git revert` undoes like `reset` | ⚠️ **Revert makes a NEW commit — correct on shared branches** (§4 → `ghjira-git-data-model-branching-and-recovery`) |
| Git Flow is the professional standard | ⚠️ **Built for versioned releases; overkill for web apps** (§3 → `ghjira-git-data-model-branching-and-recovery`) |
| Bigger PRs are more efficient to review | ⚠️ **Defect detection drops sharply with size** (§6 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| A GitHub team can deny access | ⚠️ **Permissions are additive; there is no deny** (§5 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Required checks always block | ⚠️ **A skipped workflow never reports — PR hangs** (§7 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| `pull_request_target` is a safer trigger | ⚠️ **It's a secrets-exfiltration footgun** (§8 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Pinning an action to a tag is fine | ⚠️ **Tags are mutable. Pin the SHA** (§8 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Scrub the leaked secret from history | ⚠️ **ROTATE first. Removal doesn't undo exposure** (§9 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| Use a PAT for the automation | ⚠️ **Use a GitHub App** (§11 → `ghjira-github-repos-reviews-actions-security-and-identity`) |
| GHAS is one product | ⚠️ **Split into Secret Protection and Code Security** (§26.2) |
| Copilot is flat-rate per seat | ⚠️ **Usage-based AI credits since June 2026** (§26.2) |
| Editing a Jira workflow affects one project | ⚠️ **Schemes are shared. Check first** (§13 → `ghjira-jira-configuration-workflows-and-jql`) |
| Team-managed vs company-managed is cosmetic | ⚠️ **No clean conversion path** (§14 → `ghjira-jira-configuration-workflows-and-jql`) |
| `status != Done` finds open issues | ⚠️ **Misses other terminal statuses. Use resolution** (§16 → `ghjira-jira-configuration-workflows-and-jql`) |
| Story points are hours | ⚠️ **Relative size; converted empirically by throughput** (§17 → `ghjira-jira-boards-automation-permissions-and-hygiene`) |
| Velocity compares teams | ⚠️ **It doesn't, and using it that way inflates points** (§17 → `ghjira-jira-boards-automation-permissions-and-hygiene`, §24 → `ghjira-integration-metrics-and-anti-patterns`) |
| Burndown shows what happened | ⚠️ **Burnup shows scope change; burndown hides it** (§18 → `ghjira-jira-boards-automation-permissions-and-hygiene`) |
| More statuses means better tracking | ⚠️ **More places to be inaccurate** (§15 → `ghjira-jira-configuration-workflows-and-jql`) |
| DORA metrics measure developers | ⚠️ **Team diagnostics. Individual use destroys them** (§24 → `ghjira-integration-metrics-and-anti-patterns`) |
| Speed and stability trade off | ⚠️ **DORA finds high performers do better on both** (§24 → `ghjira-integration-metrics-and-anti-patterns`) |
| Data Center is fine until 2029 | ⚠️ **New-customer sale ended March 2026; expansions end 2028** (§26.1) |
| We're an existing DC customer, so we're covered | ⚠️ **Evaluated per product and per entity** (§26.1) |

---
