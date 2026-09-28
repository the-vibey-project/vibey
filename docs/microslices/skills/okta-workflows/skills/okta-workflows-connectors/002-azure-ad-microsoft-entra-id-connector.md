---
id: skill-azure-ad-microsoft-entra-id-connector-531e51af99
purpose: azure ad microsoft entra id connector
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-connectors/SKILL.md
requires: ["skill-okta-connector-fc8833e9b9"]
links: []
---

## Azure AD / Microsoft Entra ID connector

### Quirk 5.5 — Delegated permissions only, tied to a signed-in account

"The connection uses delegated access and delegated permissions, not app-only access or app-only
permissions." The token is tied to an admin/user account — there is NO app-only/service-principal
option. Use a dedicated service account.

- *Source:* guidanceforazureadconnector.htm

### Quirk 5.6 — Reauthorization breaks when config/scopes change

"You can also reauthorize any existing connections if the admin hasn't changed any configuration
settings." Changing scopes/config can break simple reauthorization and force a full reconnect.

- *Source:* guidanceforazureadconnector.htm

### Quirk 5.7 — Three different record caps across Entra cards (correcting a common misconception)

- Azure AD **Search Groups**: "The Search Groups action card returns a maximum of 4,000 groups."
- Azure AD **Search Group Members**: caps at **900** records — the Result Set option is documented
  verbatim as "`First 900 Matching Records`: returns the first 900 records that match the search
  criteria" (NOT 4,000). Exceed via Stream Matching Records.
- Azure AD **Search Users**: "returns a maximum of 4,000 users."
- Search Group Members input "can't contain the `#` hash character" (verbatim CAUTION).

- *Sources:* azuread/actions/searchgroups.htm; azuread/actions/searchgroupmembers.htm;
  azuread/actions/searchusers.htm

### Quirk 5.8 — Mail-enabled security groups & distribution groups silently fail

"Attempting to manage a Microsoft Entra ID Mail-enabled security group or Distribution group using the
Okta workflows Azure Active Directory connector will fail… This can occur with any of the action
cards… such as Update Group, Add User to Group, etc." — because the Graph API treats these as
read-only. Workaround: manage O365/unified groups instead, or use the on-premises PowerShell template.

- *Source:* support.okta.com
  can-okta-workflows-be-used-to-manage-office-365-mail-enabled-security-groups-and-distribution-groups

### Quirk 5.9 — List Contact Folder returns max 2 levels

"The List Contact Folder card returns a maximum of two levels of child folders." Workaround: Custom
API Action with nested `$expand=childFolders($expand=childFolders)`.

- *Source:* guidanceforazureadconnector.htm

### Quirk 5.10 — Search cards that hard-code `domain` return incomplete results (pattern)

Documented for Google Workspace (cards hard-code the authorizing user's `domain` instead of
`customer`, returning single-domain results only; fix via Custom API Action with Customer ID). This is
a recurring pattern — Workflows "Search" cards often wrap fuzzy or scoped APIs, so post-filtering and
Custom API Action are the standard escapes.

- *Source:* support.okta.com Workflows-Google-Workspace-Search-Users-or-Search-Groups
