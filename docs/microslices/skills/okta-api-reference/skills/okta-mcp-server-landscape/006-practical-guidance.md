---
id: skill-practical-guidance-f8534fb6b5
purpose: practical guidance
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-mcp-server-landscape/SKILL.md
requires: ["skill-no-okta-affiliated-iga-mcp-server-exists-58da8cc08c"]
links: []
---

## Practical guidance

1. For AI-agent automation of **core** Okta resources: adopt the official `okta/okta-mcp-server`,
   authenticate with Private Key JWT outside of local dev, grant only the `*.read` scopes actually
   needed, add `*.manage` scopes per-task, and pin to a specific Git SHA (not `main`) since it ships
   with no formal releases and is explicitly labeled beta/not-for-production by Okta itself.
2. For AI-agent automation of **Identity Governance**: do not deploy
   `ashwinramn/okta-mcp-em-python` in a production context — it is unreviewed, SSWS-only, and covers
   a narrow CSV/bundle/SoD slice, not campaigns or access requests. Either wait for Okta's official
   server to add `okta.governance.*` tools, or build a small in-house MCP server wrapping only the
   OIG REST endpoints actually needed (campaigns + access requests are typically the
   highest-value pair) — the `mcp` Python SDK plus a few dozen lines of `httpx` calling the raw
   governance API (see `okta-iga-governance-api`) is sufficient for a focused internal server.
3. Re-verify tool inventories and auth models before relying on any specific third-party server
   listed here — this ecosystem changes quickly and none of these projects have Okta's backing.
4. Watch for two threshold signals that would change the above guidance: (a) Okta's official server
   adding `okta.governance.*` scopes or campaign/access-request tools — switch immediately and
   retire any in-house wrapper; (b) an `okta-iga` package appearing on PyPI under the official
   `okta` GitHub organization — adopt it in place of raw HTTP once it exists.
