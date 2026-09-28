---
id: skill-okta-connector-fc8833e9b9
purpose: okta connector
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-connectors/SKILL.md
requires: []
links: ["skill-azure-ad-microsoft-entra-id-connector-531e51af99"]
---

## Okta connector

### Quirk 5.1 — Search Groups uses exact `eq` only (except Custom Search Criteria)

"The card performs an eq (equal) comparison against the provided input value, except for the Custom
Search Criteria input." For starts-with/contains you must use the Custom Search Criteria field (`sw`,
`ew`, etc.).

- *Source:* okta/actions/searchgroups.htm

### Quirk 5.2 — Group `Type` semantics for APP_GROUP filtering

On the Okta Search Groups card: `OKTA_GROUP` = "managed either directly in Okta through static
assignments, or indirectly through group rules"; `APP_GROUP` = "imported and must be managed within
the app (such as Active Directory or LDAP) that imported the group"; `BUILT_IN` = "Okta manages the
group profile and memberships and can't be modified." When syncing Entra-imported groups on the Okta
side, filter Type = APP_GROUP — but because the card uses simple `eq`, unexpected filtering usually
means you need Custom Search Criteria or the Custom API Action card. **No confirmed public bug report
of APP_GROUP filtering misbehaving was found — treat any such claim as UNCONFIRMED.**

- *Source:* okta/actions/searchgroups.htm

### Quirk 5.3 — Search Group Rule card does keyword (not exact) search

"The search function executes a keyword search rather than an exact string match… the API searches for
the provided keywords across the Name, Expression Conditions, and Group Assignments fields… even the
First Matching Record option returns an unexpected group rule." Workaround: return the list (First 200
/ Stream) then Filter or Find for an exact name match.

- *Source:* support.okta.com okta-workflows-search-group-rule-card-returns-unexpected-multiple-results
  (updated May 6, 2026)

### Quirk 5.4 — Okta connector concurrency/rate limits differ from raw API

Built-in Okta connector: 30 concurrent Workflows → Okta requests, 15 concurrent GET/READ per-user
requests, 6,000 requests/minute total. These requests do NOT appear in the rate-limits dashboard.
DynamicScale/Workforce multipliers raise the concurrent ceiling (5x=50, 10x=80, 25x=120, 50x=150).

- *Source:* workflows-system-limits.htm
