---
id: skill-official-server-okta-okta-mcp-server-6770c465f6
purpose: official server okta okta mcp server
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-mcp-server-landscape/SKILL.md
requires: ["skill-tl-dr-00d59351ef"]
links: ["skill-third-party-alternatives-core-platform-not-okta-published-1d350bb72e"]
---

## Official server: `okta/okta-mcp-server`

- **Repository**: `github.com/okta/okta-mcp-server` — Apache-2.0, Python, Okta-published.
  Announced September 22, 2025 on `developer.okta.com`.
- **Status**: still described by Okta as **beta**, "not recommended for production use or critical
  workloads." As of the source snapshot the repo had no formal GitHub releases published.
- **Distribution**: **not on PyPI**. Install only via `git clone` + `uv sync` + `uv run
  okta-mcp-server`, or the published Docker image.
- **Transport**: stdio (compatible with Claude Desktop, VS Code Copilot, Cursor, etc.), configured
  via `mcp.json` / `claude_desktop_config.json`.
- **Authentication to Okta**: OAuth 2.0 only — either the **Device Authorization Grant**
  (interactive, browser-based; suited to local dev) or **Private Key JWT** (browserless; suited to
  headless/Docker/CI deployments). Configured via `OKTA_ORG_URL`, `OKTA_CLIENT_ID`, `OKTA_SCOPES`,
  `OKTA_PRIVATE_KEY`, `OKTA_KEY_ID` environment variables. Under the hood it uses Okta's Python SDK
  (a specific version pin was v3.4.1 in the source snapshot — verify current) for API calls.
- **Tools exposed** (by category):
  - *Users*: `list_users`, `get_user`, `create_user`, `update_user`, `deactivate_user`,
    `delete_deactivated_user`, `get_user_profile_attributes`
  - *Groups*: `list_groups`, `get_group`, `create_group`, `update_group`, `delete_group`,
    `list_group_users`, `list_group_apps`, `add_user_to_group`, `remove_user_from_group`
  - *Applications*: `list_applications`, `get_application`, `create_application`,
    `update_application`, `delete_application`, `activate_application`, `deactivate_application`
  - *Policies / Policy Rules*: full CRUD plus activate/deactivate for both policies and rules
  - *Logs*: `get_logs`
  - Plus deprecated fallback `confirm_delete_*` tools for MCP clients that don't yet support the MCP
    Elicitation API.
- **Safety features**: scope-based tool loading (a tool whose required scope isn't present in
  `OKTA_SCOPES` is hidden rather than exposed-and-failing); MCP Elicitation for destructive-operation
  confirmation; a full audit trail via the Okta System Log (every tool call is still a normal,
  logged Okta API call).
- **Zero governance coverage**: the tool registry contains no governance-prefixed tools, its
  `.env.example` lists only `okta.users.read okta.groups.read` as example scopes, and its README's
  feature list explicitly covers "users, groups, applications, policies, device assurance policies,
  brands, themes, custom pages, email templates, custom domains, email domains, and more" —
  Identity Governance is not mentioned. It also pins the core `okta` SDK, which itself doesn't wrap
  governance endpoints (see `okta-iga-governance-api`), so there's no governance capability to
  surface even indirectly. The source this was distilled from noted that the MCP server's 2026
  release notes documented only the addition of MCP Elicitation for destructive-action confirmation
  — no governance tools had been added as of that release.
