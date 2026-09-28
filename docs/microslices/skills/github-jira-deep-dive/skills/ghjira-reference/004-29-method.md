---
id: skill-29-method-bd313c886a
purpose: 29 method
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-reference/SKILL.md
requires: ["skill-28-quick-reference-c4cc234a80"]
links: []
---

## §29. Method

**§1–§25 → `ghjira-git-data-model-branching-and-recovery`, `ghjira-github-repos-reviews-actions-security-and-identity`, `ghjira-jira-configuration-workflows-and-jql`, `ghjira-jira-boards-automation-permissions-and-hygiene`, `ghjira-integration-metrics-and-anti-patterns` rests on stable mechanics** — **Git's object model, the permission and scheme
architectures, JQL semantics, review and flow research, and the DORA findings.**
⚠️ **The Git internals in §2 → `ghjira-git-data-model-branching-and-recovery` have been unchanged since 2005 and are the most durable
content here.**

**Two searches were run in August 2026**, on **Atlassian's Data Center wind-down** and
**GitHub's security and Copilot repackaging** — ⚠️ **the two changes with real budget and
migration consequences.**

**Confidence.** **High** in §2 → `ghjira-git-data-model-branching-and-recovery`, §13 → `ghjira-jira-configuration-workflows-and-jql` and §14 → `ghjira-jira-configuration-workflows-and-jql`, which are the sections I'd most want read.
⚠️ **The "commits are snapshots, branches are pointers" framing dissolves most Git
confusion**, **and §13 → `ghjira-jira-configuration-workflows-and-jql`'s shared-scheme gotcha plus §14 → `ghjira-jira-configuration-workflows-and-jql`'s irreversible project-type choice
are the two ways people most commonly damage a Jira instance without realizing it at the
time.**

**High** in §26.1's timeline, which comes from Atlassian's own licensing pages and is
corroborated across multiple partner and analyst sources: ⚠️ **price increases 17 February
2026, end of sale to new customers 30 March 2026, end of expansions 30 March 2028, end of
life 28 March 2029.** ⚠️ **The per-product and per-entity "existing customer" definition is
the detail I'd most want flagged** — **it's specific, it's counterintuitive, and it catches
organizations mid-expansion or mid-acquisition.** **The percentage increases (~15% standard,
18–40% legacy Advantage) come from partner and reseller commentary rather than
Atlassian's own pricing page, so treat those as reported.**

**High** in §26.2's GHAS split and pricing, which trace to GitHub's own changelog and
resources pages. ⚠️ **The Copilot AI-credits transition (1 June 2026) and the reported
58-day sign-up freeze from 20 April 2026 come from secondary tech coverage rather than
GitHub's own announcements in my results** — **I've attributed them as reported.**
⚠️ **The generalizable point is mine and I think it's the useful takeaway: flat-rate
pricing does not survive agentic usage, so per-seat budget assumptions for AI coding tools
should be expected to break.**

⚠️ **Sourcing caution specific to this file**: **much of the Atlassian material comes from
migration consultancies and competing vendors, who have an obvious interest in urgency
around Data Center EOL.** **I anchored the dates on Atlassian's own pages and used the
partner sources only for the price-increase percentages and the practical implications,
flagging those as reported.** ⚠️ **Similarly, several GitHub pricing figures come from
third-party pricing-guide sites; the product names, split, and per-active-committer
billing unit are confirmed by GitHub's own changelog.**
