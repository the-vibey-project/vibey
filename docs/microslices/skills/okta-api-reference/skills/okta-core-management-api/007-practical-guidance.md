---
id: skill-practical-guidance-f383c12129
purpose: practical guidance
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: ["skill-the-official-python-sdk-okta-6479b7c855"]
links: []
---

## Practical guidance

1. Default to OAuth 2.0 Private Key JWT with narrowly-scoped `okta.*.read` scopes for any
   long-lived integration; add `*.manage` scopes per-task rather than provisioning them broadly
   up front, and audit which scopes are actually exercised periodically.
2. Reserve SSWS tokens for throwaway scripts and local experimentation only — never wire them into
   a production service, given Okta's own recommendation against the scheme and its lack of
   scoping.
3. Always follow `Link` headers for pagination (both general resource lists and the System Log) —
   never hand-roll offset math against Okta's cursor-based pagination contract.
4. Before assuming the official Python SDK covers an endpoint, check whether it's a Management API
   path (`/api/v1/...`) or a Governance path (`/governance/api/...`) — only the former is in scope
   for the `okta` package as of this snapshot.
