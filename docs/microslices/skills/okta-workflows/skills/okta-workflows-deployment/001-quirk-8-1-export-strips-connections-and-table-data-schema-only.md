---
id: skill-quirk-8-1-export-strips-connections-and-table-data-schema-only-cf719000c0
purpose: quirk 8 1 export strips connections and table data schema only
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-deployment/SKILL.md
requires: []
links: ["skill-quirk-8-2-broken-references-require-manual-remapping-on-import-e64441aad4"]
---

## Quirk 8.1 — Export strips connections and table DATA (schema only)

"The export function removes all connection information and table data." On import, "you need to
restore all card connections" and "tables are recreated according to the table schema… but the tables
are initially empty." Critical when moving Preview/sandbox → Production.

- *Sources:* about-folders.htm; export-import-flows.htm
