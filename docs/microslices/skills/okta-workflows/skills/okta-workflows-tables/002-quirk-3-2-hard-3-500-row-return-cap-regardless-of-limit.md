---
id: skill-quirk-3-2-hard-3-500-row-return-cap-regardless-of-limit-0fddceda8d
purpose: quirk 3 2 hard 3 500 row return cap regardless of limit
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-tables/SKILL.md
requires: ["skill-quirk-3-1-search-rows-searchrows2-is-case-sensitive-38a1887416"]
links: ["skill-quirk-3-3-table-hard-limits-8a775175e3"]
---

## Quirk 3.2 — Hard 3,500-row return cap regardless of Limit

"Regardless of the limit selected, the function card returns a maximum of 3,500 rows from the
selected table" (stash_searchrows2.htm). Confirmed independently by Max Katz "Workflows Tips #36"
(maxkatz.net, 2022/09/09): "If a filter or limit is not applied to the table search, a maximum of
3,500 rows from the selected table will be read by the Search Rows function card." Critical for
sync-reconciliation tables that can grow large.

- *Workaround:* Page with the Offset input (0-based) in a recursive/paginated helper flow, or design
  tables to be queried by indexed key columns returning fewer than 3,500 rows.
