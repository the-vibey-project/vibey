---
id: skill-recent-platform-changes-2025-2026-d2c6e03cc2
purpose: recent platform changes 2025 2026
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-field-guide/SKILL.md
requires: ["skill-recommendations-c339ad9224"]
links: ["skill-caveats-b51642095f"]
---

## Recent Platform Changes (2025–2026)

- **2025.05.1:** Okta ITP connector added (Global Token Revocation, Retrieve/Upsert User Risk,
  Universal Logout, etc.); **Send Slackbot Message card fully deprecated** — update flows or they
  error; fix OKTA-928020 (space-only or duplicate names for folders/flows/tables were previously
  allowed).
- **2025.06.1:** Smartsheet sheet-count deprecated; fix OKTA-858112 (Zendesk List Group Members
  didn't return all members); fix for Branching Lookup values starting with a number and containing
  text not saving correctly.
- **2025 broader:** Connector Builder Polling Monitors (custom event triggers for APIs without
  webhooks); AI-agent events became event-hook-eligible; root CA certificate baseline updated to Dec
  31, 2024 (CAs removed from the Common CA DB after Mar 11, 2023 deprecated in 2025.03.0); fix
  OKTA-946866 ("In Workflows, the Okta Connector app didn't display a list of available connector
  actions").
- *Sources:* help.okta.com Workflows production release notes; workflows-version-history.htm;
  devforum.okta.com 2025.06.1 release thread.
