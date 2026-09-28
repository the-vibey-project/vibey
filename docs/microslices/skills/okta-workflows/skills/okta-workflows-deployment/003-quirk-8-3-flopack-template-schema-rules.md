---
id: skill-quirk-8-3-flopack-template-schema-rules-a1e74216ae
purpose: quirk 8 3 flopack template schema rules
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-deployment/SKILL.md
requires: ["skill-quirk-8-2-broken-references-require-manual-remapping-on-import-e64441aad4"]
links: ["skill-quirk-8-4-max-folder-depth-5-duplicate-folder-doesn-t-copy-table-data-5a2356949a"]
---

## Quirk 8.3 — flopack/template schema rules

`workflow.flopack` and `workflow.json` must be valid JSON; the `name` value has a 50-char limit and
must exactly match the enclosing folder; connector names must match `connectors.json`; folder name
must satisfy regex `^[a-z0-9_]{2,50}$`. The `details` object (flowCount, helperFlowsCount,
mainFlowsCount, `flos[]` with id/name/type/screenshotURL, tags) must exactly match the flopack or CI
validation fails.

- *Source:* github.com/okta/workflows-templates README
