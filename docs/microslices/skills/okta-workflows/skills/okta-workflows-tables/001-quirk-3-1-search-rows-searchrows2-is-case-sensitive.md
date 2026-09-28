---
id: skill-quirk-3-1-search-rows-searchrows2-is-case-sensitive-38a1887416
purpose: quirk 3 1 search rows searchrows2 is case sensitive
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-tables/SKILL.md
requires: []
links: ["skill-quirk-3-2-hard-3-500-row-return-cap-regardless-of-limit-0fddceda8d"]
---

## Quirk 3.1 — Search Rows (searchRows2) is case-sensitive

The Search Rows card documentation states plainly: "The search expression is case sensitive." Numeric
conditions are fine; text matching fails on case mismatch, and there is no "starts with" for text.

- *Workaround:* Normalize case with a Text - To Lower Case card before writing AND before searching,
  or pull all rows and use a List - Filter (Custom) helper flow to perform case-insensitive/starts-with
  matching.
- *Sources:* Okta docs stash_searchrows2.htm; support.okta.com
  searching-a-table-using-a-custom-filter-in-workflows; maxkatz.net 2024/01/19
