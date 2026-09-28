---
id: skill-quirk-8-2-broken-references-require-manual-remapping-on-import-e64441aad4
purpose: quirk 8 2 broken references require manual remapping on import
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-deployment/SKILL.md
requires: ["skill-quirk-8-1-export-strips-connections-and-table-data-schema-only-cf719000c0"]
links: ["skill-quirk-8-3-flopack-template-schema-rules-a1e74216ae"]
---

## Quirk 8.2 — Broken references require manual remapping on import

"If any of the imported flows refer to a flow that wasn't included in the export (for example, a helper
flow called to handle a list), you must specify a replacement flow to complete the import." Missing
references are flagged and block completion until resolved.

- *Sources:* export-import-flows.htm; about-folders.htm
