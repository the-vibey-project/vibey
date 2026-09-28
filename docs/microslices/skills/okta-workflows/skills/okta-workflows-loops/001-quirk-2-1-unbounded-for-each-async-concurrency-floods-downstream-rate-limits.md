---
id: skill-quirk-2-1-unbounded-for-each-async-concurrency-floods-downstream-rate-limits-3966088057
purpose: quirk 2 1 unbounded for each async concurrency floods downstream rate limits
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-loops/SKILL.md
requires: []
links: ["skill-quirk-2-2-for-each-ignore-errors-only-ignores-errors-from-the-parent-s-perspective-30413b3f3c"]
---

## Quirk 2.1 — Unbounded For Each / async concurrency floods downstream rate limits

"For Each - Ignore Errors" (the `asyncEach` card) takes a `concurrency` (Number) input: "Number of
items in the list to process in parallel. If it is important that the items are processed in
sequence, use 1. Otherwise a higher number like 5 or 10 will cause your flow to complete sooner."
With no throttle, parallel branch executions each fire Okta/Graph API calls and hit the Okta
connector's hard concurrency ceiling (30 concurrent Workflows → Okta org requests; 15 concurrent GET
/users/{id}). A 429 due to a concurrency limit shows a `core.concurrency.org.limit.violation` event
in the System Log.

- *Workaround:* Set `concurrency` explicitly (1 for strict ordering; 5–10 for throughput, staying
  well under the connector ceiling). For very large lists prefer Stream Matching Records, which
  paginates with low memory.
- *Sources:* Okta docs list_asynceach.htm, architecture-best-practices.htm, developer.okta.com
  rl2-concurrency
- *Note:* Two distinct concurrency numbers apply. The **Okta connector** limit is 30 concurrent
  Workflows → org requests (workflows-system-limits.htm). The **org-wide** API concurrency limit is a
  separate default of 75 simultaneous transactions, tracked separately for Microsoft 365 vs. all
  other traffic (developer.okta.com rl2-concurrency). Design against whichever applies to the
  specific card.
