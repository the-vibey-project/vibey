---
id: skill-11-api-apps-and-webhooks-c066003226
purpose: 11 api apps and webhooks
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: ["skill-10-issues-and-projects-502e136fab"]
links: ["skill-12-enterprise-identity-7a93c9386e"]
---

## §11. API, Apps and Webhooks

```
REST v3        broad, paginated, rate-limited
⚠️ GraphQL v4  ⚠️ fetch exactly what you need in one call. Far better for
   nested data; ⚠️ some operations exist ONLY in one API or the other
WEBHOOKS       ⚠️ verify the HMAC signature. Handle retries and duplicates —
   delivery is at-least-once, so make handlers IDEMPOTENT
```
**⚠️ Authentication choices, and this matters:**
```
⚠️ PAT (classic)         broad scopes, tied to a USER. Avoid for automation
⚠️ Fine-grained PAT      per-repo, per-permission, expiring. Better
⚠️ GITHUB APP            ⚠️ THE right answer for automation: own identity,
   granular permissions, higher rate limits, short-lived installation
   tokens, survives the creator leaving the company
⚠️ OIDC                  for cloud deploys — no stored secret at all (§8)
```
**⚠️ The failure mode a PAT creates**: ⚠️ **automation tied to an individual breaks when
that person's access changes or they leave**, **and it grants their full permissions rather
than the minimum needed.** **Use an App.**

---
