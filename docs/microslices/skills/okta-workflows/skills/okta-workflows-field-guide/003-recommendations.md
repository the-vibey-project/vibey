---
id: skill-recommendations-c339ad9224
purpose: recommendations
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-field-guide/SKILL.md
requires: ["skill-key-findings-8d4ee09083"]
links: ["skill-recent-platform-changes-2025-2026-d2c6e03cc2"]
---

## Recommendations

1. **Immediately (design phase):** Standardize a type-coercion convention — every comparison
   explicitly sets both operand types; normalize all string keys to lower case before Table writes
   AND searches. Build one central error-logging helper flow that writes failures (with the Caller
   `root_wf_id`) to a dedicated Errors table.
2. **Before any bulk sync:** Replace all unbounded loops with For Each - Ignore Errors at
   `concurrency=5` (tune down to 1 if you see `core.concurrency.org.limit.violation` in the System
   Log; raise toward 10 only if well under the 30-concurrent Okta-connector ceiling). For more than
   900 Entra group members, more than 4,000 Entra groups/users, or more than 3,500 Table rows,
   switch to Stream Matching Records or Offset-based pagination.
3. **For state across pages:** Do not rely on the streaming `State` object as an accumulator —
   persist run state to a Tables row keyed by run ID, or implement the Connector Builder Paginate
   `object` / `break` / `path` do-while pattern.
4. **For Preview → Production promotion:** Script re-creation of connections and re-population of
   lookup tables post-import; keep helper flows in the same exported folder to preserve references;
   validate flopack `name` / folder-name match and connector names before import.
5. **Guardrails/benchmarks that change the plan:** If event volume approaches 280,000/day
   (event-hook warning threshold) or 400,000/day (hard cutoff), or if flows get throttled, move from
   event-driven to scheduled batch sync and/or purchase DynamicScale. If synchronous API-endpoint
   flows approach 60s, refactor with API Connector Close + Call Flow Async.
6. **Entra specifics:** Use a dedicated Entra service *user* account (delegated auth only — no
   app-only); exclude mail-enabled security/distribution groups from sync (they will fail on write
   cards); avoid `#` in Search Group Members inputs; and fully re-connect (not merely reauthorize)
   whenever you change connector scopes.
