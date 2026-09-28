---
id: skill-quirk-8-4-max-folder-depth-5-duplicate-folder-doesn-t-copy-table-data-5a2356949a
purpose: quirk 8 4 max folder depth 5 duplicate folder doesn t copy table data
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-deployment/SKILL.md
requires: ["skill-quirk-8-3-flopack-template-schema-rules-a1e74216ae"]
links: []
---

## Quirk 8.4 — Max folder depth 5; duplicate-folder doesn't copy table data

An import that would exceed 5 levels is offered as a top-level folder instead. Duplicating a folder
copies table schema but not data (must be transferred manually); references within the folder repoint
to duplicates, external references stay unchanged; creation dates reset to the duplication date.

- *Sources:* export-import-flows.htm; about-folders.htm
