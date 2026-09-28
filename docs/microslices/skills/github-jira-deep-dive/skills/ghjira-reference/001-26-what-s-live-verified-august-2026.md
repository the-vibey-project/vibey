---
id: skill-26-what-s-live-verified-august-2026-478ba2553c
purpose: 26 what s live verified august 2026
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-reference/SKILL.md
requires: []
links: ["skill-27-misconceptions-fcbc29e466"]
---

## §26. What's Live — verified August 2026

> **⚠️ Both vendors reprice and repackage frequently. Everything below carries a date;
> verify against the vendor before committing budget.**

### 26.1 ⚠️ Atlassian: Data Center is ending, and the dates are the whole story
**⚠️ If you run self-managed Atlassian, this is a migration project with a deadline, not a
watching brief.**

- **⚠️ Announced 8 September 2025.** **The timeline as published:**
```
⚠️ 17 Feb 2026   Data Center PRICE INCREASES take effect (~15% standard list;
                 ⚠️ reported 18–40% for legacy "Advantage" pricing depending
                 on tier, as those are brought to standard list)
⚠️ 30 Mar 2026   END OF SALE for NEW customers. After this, Cloud is the only
                 entry point to the Atlassian ecosystem
⚠️ 30 Mar 2028   Last date EXISTING customers can buy new licences, app
                 licences or tier expansions. After that: renewal only
⚠️ 28 Mar 2029   END OF LIFE. Instances go READ-ONLY; no support, no updates
```
- **⚠️ Affected products include Jira Software, Jira Service Management, Confluence,
  Bamboo and Crowd.** ⚠️ **Bitbucket Data Center is treated differently — reported dual
  licensing for Bitbucket DC and Cloud, recognizing on-prem source-code requirements —
  though sources characterize that as a reprieve rather than a permanent exemption.**
- **⚠️ Feature development for Data Center has effectively stopped**; **innovation is in
  Cloud only.**

> **⚠️ GOTCHA — the "existing customer" definition is narrower than people assume and it
> catches organizations off guard.** ⚠️ **Status is evaluated PER PRODUCT: if you run
> Jira Software on Data Center today but want to add Jira Service Management on Data
> Center, you are a NEW customer for that product and cannot.**
> **⚠️ It's also evaluated per entity — a parent company's Data Center licences cannot be
> extended to cover a newly acquired subsidiary after March 2026.** **⚠️ This matters
> enormously for M&A and for phased platform expansion.**

**⚠️ Constrained environments have a genuine problem, and it should be named**:
⚠️ **air-gapped deployments have no Atlassian Cloud option; Atlassian's Isolated Cloud
(expected 2026) is reported as internet-connected and Atlassian-managed.** ⚠️ **Government
Cloud has a much smaller app ecosystem — around 60 Marketplace apps versus 4,000+
commercially — with apps needing rebuilding as Forge apps.** **⚠️ And Jira Align has no
reported compliant cloud path for some regulated users, which makes SAFe portfolio
management a separate tooling decision.**
**⚠️ Rovo is the other commercial change to watch**: **Atlassian's AI layer, reported at
$20/user/month on Cloud Premium and Enterprise** — ⚠️ **the most expensive Atlassian
add-on, and appearing in enterprise renewal quotes.** **⚠️ Reported pricing model has
shifted twice since launch; treat the number as a snapshot and evaluate genuine
utilization before committing.**

### 26.2 ⚠️ GitHub: security unbundled, Copilot repriced twice
- **⚠️ GitHub Advanced Security no longer exists as a single SKU.** **From 1 April 2025 it
  was split into two standalone products:**
```
⚠️ GITHUB SECRET PROTECTION  $19/month per ACTIVE COMMITTER
   push protection, secret scanning, AI-powered detection
⚠️ GITHUB CODE SECURITY      $30/month per active committer
   code scanning, Copilot Autofix, security campaigns, Dependabot
   features, dependency review, security overview
```
⚠️ **Crucially, GitHub Team plan customers can buy these without an Enterprise
subscription — which materially lowers the entry point for smaller orgs.**
**⚠️ Note the billing unit: ACTIVE COMMITTER, not seat.** **That's a different and usually
smaller denominator than your licence count, and it makes cost modelling non-obvious.**
- **⚠️ Free assessment tooling arrived**: **a Secret Risk Assessment and, more recently, a
  Code Security Risk Assessment giving a free one-click CodeQL scan of up to 20 active
  repositories with no licence required and no Actions minutes consumed.** ⚠️ **That's a
  genuinely useful way to size your exposure before buying anything.**

> **⚠️ GOTCHA — Copilot's billing model changed fundamentally, and the reason is
> instructive.** ⚠️ **All Copilot plans moved to usage-based AI CREDIT billing on 1 June
> 2026 (reported at $0.01 per credit), with costs tracking actual model usage rather than
> a fixed request count.**
> **⚠️ The driver was agentic workloads: GitHub paused new sign-ups for Pro, Pro+ and
> Student plans in a reported 58-day freeze beginning 20 April 2026**, ⚠️ **with GitHub's
> VP of Product attributing it to long-running parallelized agentic sessions consuming far
> more resources than flat-rate plans could support.**
> **⚠️ Sign-ups reopened gradually from 17 June 2026, per GitHub's own changelog, and a
> new $100/month Max plan was added** alongside Free, Pro and Pro+ — **$200 in monthly AI
> credits and roughly 2.9× Pro+'s usage headroom.**
> **⚠️ The generalizable lesson: flat-rate pricing does not survive agentic usage
> patterns, and anyone budgeting for AI coding tools on a per-seat assumption should
> expect that assumption to break.**

- **⚠️ Agentic features moved from autocomplete to delegated work.** **Copilot coding agent
  can be assigned a GitHub Issue, works asynchronously in an ephemeral Actions-powered
  environment on a branch, and opens a PR for human review.** ⚠️ **Agentic code review
  shipped around March 2026.** **⚠️ The human-review-before-merge gate is the important
  design point, and your rulesets (§7 → `ghjira-github-repos-reviews-actions-security-and-identity`) are what enforce it.**
- **⚠️ Rulesets continue to displace classic branch protection** — **automatic conversion
  of branch protection rules into rulesets is now available, along with a rule insights
  dashboard showing blocked-push trends over time.**
- **⚠️ Actions**: **custom runner autoscaling, expanded security controls, and reported
  hosted-runner price reductions of up to 39% in January 2026.** ⚠️ **Also note read-only
  cache tokens for workflows triggerable without write permissions — a supply-chain
  hardening change.**

---
