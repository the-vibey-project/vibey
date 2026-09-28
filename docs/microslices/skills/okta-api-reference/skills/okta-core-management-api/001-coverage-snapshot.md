---
id: skill-coverage-snapshot-7f23fb0db5
purpose: coverage snapshot
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: []
links: ["skill-rest-api-basics-bf4d5132a1"]
---

## Coverage snapshot

The Okta core (Workforce/Customer Identity) platform has full coverage on all three integration
dimensions as of the source snapshot: a mature REST/Management API authenticated by SSWS token or
OAuth 2.0; an official Python SDK on PyPI (package `okta`); and an official Okta-published MCP
server (`okta/okta-mcp-server`, announced September 22, 2025) — though that MCP server is still
distributed source-only via `uv`/Docker (not on PyPI) and Okta itself still labels it beta. See
`okta-mcp-server-landscape` for the full MCP picture.
