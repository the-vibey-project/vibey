---
id: skill-8-github-actions-0124609904
purpose: 8 github actions
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: ["skill-7-rulesets-and-branch-protection-2993182716"]
links: ["skill-9-security-products-1dad34cbc8"]
---

## §8. GitHub Actions

```
WORKFLOW → JOBS → STEPS.  Jobs run in parallel by default; ⚠️ `needs` sequences them
TRIGGERS  push · pull_request · ⚠️ pull_request_target (SEE THE GOTCHA) ·
   schedule · workflow_dispatch · workflow_call (reusable) · repository_dispatch
RUNNERS   GitHub-hosted vs self-hosted; ⚠️ larger runners; custom autoscaling
CONTEXTS  github, env, secrets, vars, matrix
MATRIX    ⚠️ fan out across versions/OSes — the highest-value Actions feature
CACHING   actions/cache; ⚠️ cache keys and restore-keys are where it goes wrong
ARTIFACTS · ENVIRONMENTS (⚠️ with required reviewers for deploy gates) ·
CONCURRENCY groups (⚠️ cancel superseded runs — saves real money)
```
> **⚠️ GOTCHA — `pull_request_target` runs in the context of the BASE repository with
> access to secrets, and it is a well-documented security footgun.** ⚠️ **If you check
> out and execute code from the PR head under `pull_request_target`, a fork PR can
> exfiltrate your secrets.** **⚠️ Use plain `pull_request` for untrusted contributions;
> if you genuinely need `pull_request_target`, do not check out or run PR code in it.**

**⚠️ Other security essentials**: ⚠️ **pin third-party actions to a full commit SHA, not a
tag — tags are mutable and a compromised action is a supply chain compromise**; **set
`permissions:` explicitly at the top of workflows (the default token is broader than most
jobs need); ⚠️ prefer OIDC federation to cloud providers over long-lived stored
credentials; and treat self-hosted runners on public repos as dangerous unless properly
isolated.**
**⚠️ Cost control**: ⚠️ **concurrency cancellation, path filters, caching, and choosing
runner sizes deliberately.** **Actions minutes overages are a common surprise line item.**

---
