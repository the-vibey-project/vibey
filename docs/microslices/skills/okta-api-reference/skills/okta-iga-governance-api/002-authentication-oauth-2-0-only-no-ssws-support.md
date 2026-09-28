---
id: skill-authentication-oauth-2-0-only-no-ssws-support-abfe60f450
purpose: authentication oauth 2 0 only no ssws support
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-iga-governance-api/SKILL.md
requires: ["skill-base-url-and-versioning-8db4ea607d"]
links: ["skill-resource-surface-c9671154fe"]
---

## Authentication: OAuth 2.0 only — no SSWS support

Unlike the core Management API, OIG endpoints accept **only** OAuth 2.0 bearer tokens — there is no
SSWS token fallback. The token comes from either an OIDC app (user-based) or a service app
(`client_credentials` / Private Key JWT), and must include the relevant `okta.governance.*` scopes.
Representative scope names:

- `okta.governance.campaigns.read` / `.manage`
- `okta.governance.accessRequests.read` / `.manage`
- `okta.governance.entitlements.read` / `.manage`
- `okta.governance.labels.manage`
- `okta.governance.securityAccessReviews.admin.manage`
- `okta.governance.delegates.manage`

Service apps additionally need an admin role (e.g. `SUPER_ADMIN` or a custom admin role) because the
resulting access token acts *as* that principal — scopes alone aren't sufficient without the
underlying admin-role grant.
