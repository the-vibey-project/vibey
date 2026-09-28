---
id: skill-the-one-iga-focused-mcp-project-2b806612f5
purpose: the one iga focused mcp project
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-mcp-server-landscape/SKILL.md
requires: ["skill-third-party-alternatives-core-platform-not-okta-published-1d350bb72e"]
links: ["skill-no-okta-affiliated-iga-mcp-server-exists-58da8cc08c"]
---

## The one IGA-focused MCP project

`ashwinramn/okta-mcp-em-python` (`github.com/ashwinramn/okta-mcp-em-python`) is the **only** public
MCP server in this ecosystem that specifically targets Identity Governance workflows, and it comes
with significant caveats:

- MIT-licensed, Python, single author, 0 stars / 0 forks, 13 commits at the time of the source
  snapshot.
- Self-described (verbatim from its own README) as "vibe coded — built rapidly through AI-assisted
  development with Claude/Copilot. While functional and tested against real Okta tenants, it: May
  contain unconventional patterns or edge cases not fully handled · Has not undergone formal
  security review · Is provided as-is for experimentation and learning · Should be tested thoroughly
  in a sandbox environment before any production use."
- **Authentication**: legacy SSWS API token only (`OKTA_DOMAIN`, `OKTA_API_TOKEN` env vars) — no
  OAuth or scoped-token support at all.
- **Tool coverage** (by category, verbatim tool names from its README):
  - *Navigation*: `okta_test`, `show_workflow_menu`
  - *CSV import*: `list_csv_files`, `analyze_csv_for_entitlements`,
    `prepare_entitlement_structure`, `execute_user_grants`
  - *Governance & compliance*: `generate_governance_summary`, `analyze_sod_context`,
    `create_sod_risk_rule`, `list_sod_risk_rules`, `test_sod_risk_rule`
  - *Bundle mining*: `analyze_entitlement_patterns`, `preview_bundle_creation`,
    `create_bundle_from_pattern`, `create_entitlement_bundle`
  - *Utility*: `okta_user_search`, `okta_batch_user_search`, `okta_batch_create_grants`,
    `okta_get_rate_status`, `get_entitlement_ids_for_values`
- **What's missing**: no access-request creation/approval/decision tools, no campaign CRUD or
  launch/end, no review-decision tooling, no security-access-review trigger, no labels/delegates/
  collections support. Its real scope is "bulk-onboard entitlements from a CSV and create
  SoD-safe bundles" — not a general-purpose governance MCP server, despite the category name.
