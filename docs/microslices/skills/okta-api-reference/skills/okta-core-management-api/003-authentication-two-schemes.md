---
id: skill-authentication-two-schemes-5575d8bc28
purpose: authentication two schemes
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: ["skill-rest-api-basics-bf4d5132a1"]
links: ["skill-resource-surface-representative-not-exhaustive-4fb4c4d7ab"]
---

## Authentication: two schemes

1. **SSWS API token** — sent as `Authorization: SSWS {token}`. Okta's own documentation now
   recommends **against** this for new work: per the Postman setup guide
   (`developer.okta.com/docs/reference/rest/`), "Okta doesn't recommend
   using the Okta-proprietary SSWS API token authentication scheme. This API token scheme allows you
   to access a broad range of APIs because there's no scope associated with the token. Access to the
   APIs depends on the privileges of the user that created the API token. The API token also has a
   fixed expiry date." Treat SSWS as acceptable only for short-lived scripts, never as the
   authentication backbone of a persistent service.
2. **OAuth 2.0 scoped access tokens** — issued by the org authorization server at
   `https://{yourOktaDomain}/oauth2/v1/token`. Sent as `Authorization: Bearer {access_token}`.
   Service-to-service apps should use **Private Key JWT** (`client_credentials` grant). Scopes are
   granular — representative examples: `okta.users.read`, `okta.groups.manage`,
   `okta.policies.manage`, `okta.logs.read`, `okta.apps.manage`. Always request the narrowest scope
   set the calling code actually needs, and treat `*.manage` scopes as requiring more scrutiny than
   `*.read`.
