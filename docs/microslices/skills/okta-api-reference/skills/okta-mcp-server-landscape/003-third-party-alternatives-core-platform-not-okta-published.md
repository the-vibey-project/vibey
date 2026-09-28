---
id: skill-third-party-alternatives-core-platform-not-okta-published-1d350bb72e
purpose: third party alternatives core platform not okta published
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-mcp-server-landscape/SKILL.md
requires: ["skill-official-server-okta-okta-mcp-server-6770c465f6"]
links: ["skill-the-one-iga-focused-mcp-project-2b806612f5"]
---

## Third-party alternatives (core platform, not Okta-published)

None of the following advertise Identity Governance coverage — all are scoped to core IAM
(users/groups/apps/policies):

- **`fctr-id/okta-mcp-server`** ("Tako MCP") — Python; stdio + HTTP/SSE transports; API-token or
  OAuth Private Key JWT; includes risk-assessment and access-analysis tooling on top of core IAM
  resources.
- **`kapilduraphe/okta-mcp-server`** — TypeScript/Node; SSWS token auth; focused on user/group
  management and onboarding workflows.
- **`indranilokg/okta-mcp-server`** — npm-installable; app/group/user management.
- **StackOne Okta MCP** — a managed commercial offering. StackOne's own marketing states it "ships
  with 32 pre-built actions, fully extensible via the Connector Builder — plus managed
  authentication, prompt injection defense, and optimized agent context."
