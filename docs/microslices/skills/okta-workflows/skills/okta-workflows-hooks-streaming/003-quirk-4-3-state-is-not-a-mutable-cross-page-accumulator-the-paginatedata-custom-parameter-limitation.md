---
id: skill-quirk-4-3-state-is-not-a-mutable-cross-page-accumulator-the-paginatedata-custom-parameter-limitation-5985dbdf1a
purpose: quirk 4 3 state is not a mutable cross page accumulator the paginatedata custom parameter limitation
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-hooks-streaming/SKILL.md
requires: ["skill-quirk-4-2-streaming-helper-flow-contract-is-rigid-inputs-must-be-named-record-and-state-both-object-6d3f511981"]
links: ["skill-quirk-4-4-event-hook-hard-limits-and-no-ordering-guarantee-0cadf56166"]
---

## Quirk 4.3 — `State` is NOT a mutable cross-page accumulator (the paginateData custom-parameter limitation)

The docs describe `State` as parent-defined inputs sent to the helper flow with each record; there is
no documented mechanism for the helper flow to mutate `State` and have that change survive to the next
record/page. This is the structural limitation behind the user's finding that streaming Handler Flows
do not thread custom/user-defined parameters through the built-in paginate mechanism.

- *Workaround:* Implement manual cursor-based pagination. For raw HTTP, use the Connector Builder
  Paginate card, which "acts like a 'Do while' loop": pass an `object` containing a break key
  (commonly named `break`) set to FALSE plus a `path` field naming that key; the helper flow updates
  the object each iteration and *removes* the `path` key to stop. "Proper use of the path field is
  important… If it isn't properly managed, the flow could run until it hits the maximum count of 5,000
  iterations." For state that must persist across pages, externalize it to a Tables row keyed by run
  ID rather than relying on `State`.
- *Sources:* http_paginate.htm; maxkatz.net Tips #73 (recursive Okta API pagination template)
