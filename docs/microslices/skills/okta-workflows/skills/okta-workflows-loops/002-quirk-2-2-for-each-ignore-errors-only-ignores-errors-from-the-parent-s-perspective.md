---
id: skill-quirk-2-2-for-each-ignore-errors-only-ignores-errors-from-the-parent-s-perspective-30413b3f3c
purpose: quirk 2 2 for each ignore errors only ignores errors from the parent s perspective
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-loops/SKILL.md
requires: ["skill-quirk-2-1-unbounded-for-each-async-concurrency-floods-downstream-rate-limits-3966088057"]
links: ["skill-quirk-2-3-plain-for-each-returns-no-outputs-aba3a12725"]
---

## Quirk 2.2 — "For Each - Ignore Errors" only ignores errors from the PARENT's perspective

"While the card name implies that it ignores errors, this is only true from the parent flow
perspective. You can handle errors in your helper flows." A failing item won't stop the batch, but
you get no parent-level signal — implement logging/error capture inside the helper flow (e.g., write
failures to a Tables error log).

- *Source:* architecture-best-practices.htm
