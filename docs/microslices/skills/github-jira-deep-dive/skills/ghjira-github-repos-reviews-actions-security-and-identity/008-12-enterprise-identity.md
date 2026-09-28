---
id: skill-12-enterprise-identity-7a93c9386e
purpose: 12 enterprise identity
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-github-repos-reviews-actions-security-and-identity/SKILL.md
requires: ["skill-11-api-apps-and-webhooks-c066003226"]
links: []
---

## §12. Enterprise Identity

**⚠️ SAML SSO, SCIM provisioning, and the significant fork: EMU.**
> **⚠️ GOTCHA — Enterprise Managed Users (EMU) is close to irreversible and it changes
> what developers can do.** ⚠️ **With EMU, GitHub accounts are created and owned by your
> IdP; users cannot use their personal accounts, cannot contribute to public repos from
> their managed account, and cannot take contribution history with them.**
> **⚠️ It provides genuine control and is the right answer for some regulated
> environments — but decide deliberately, because migrating in or out is a project, not a
> setting.**

**⚠️ Audit log**: **streaming to a SIEM, and ⚠️ retention limits mean you should stream if
you need long-horizon forensics.**
**⚠️ IP allow lists, required 2FA, and repository visibility policies** at org and
enterprise level.

---

# PART III — JIRA
