---
id: skill-resource-surface-representative-not-exhaustive-4fb4c4d7ab
purpose: resource surface representative not exhaustive
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: ["skill-authentication-two-schemes-5575d8bc28"]
links: ["skill-system-log-polling-pattern-b38a44e25d"]
---

## Resource surface (representative, not exhaustive)

Users, Groups, Applications, Sessions, Factors/Authenticators, Policies & Policy Rules (sign-on,
password, MFA, authentication, access), Authorization Servers (with Scopes, Claims, Access Policies,
Policy Rules), System Log, Devices, Brands/Themes/Custom Pages, Email Templates/Domains, Custom
Domains, Identity Providers, Network Zones, Trusted Origins, Roles & Resource Sets, Event/Inline
Hooks, Schemas, Realms.

Endpoint path examples that appear across real integrations: `/api/v1/users`, `/api/v1/groups`,
`/api/v1/apps`, `/api/v1/policies`, `/api/v1/devices`, `/api/v1/authenticators`,
`/api/v1/behaviors`, `/api/v1/trustedOrigins`, `/api/v1/zones`, `/api/v1/logs` (System Log),
`/api/v1/org` (whoami/org info), `/api/v1/authorizationServers` (Auth Servers, Scopes, Claims,
Policies, Rules), `/api/v1/brands` (Brands, Themes, Email Customizations, Email Domains, Domains),
`/api/v1/flows` (Okta Workflows folder list, export-as-zip, import, delete — see the caveat on
Workflows below), `/api/v1/iam` (Custom Roles, Resource Sets, Role Targets, Role Assignments),
`/api/v1/security/events/providers` (Shared Signals Framework / ITP event providers), and the
ITP-specific policy endpoints under `/api/v1/policies` for entity-risk, post-auth, and
session-violation policy types.

Note on Okta Workflows: the `/api/v1/flows` endpoint only supports folder-level list/export
(zip)/import/delete — there is no API to modify Workflows logic inside a flow. Any tool that
manages Workflows folders via the API can only really do drift-*detection* on the exported bundle
(compare by hash), not field-level create/update of flow contents.
