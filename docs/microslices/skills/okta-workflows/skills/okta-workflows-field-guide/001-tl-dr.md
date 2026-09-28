---
id: skill-tl-dr-05f51c8a04
purpose: tl dr
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-field-guide/SKILL.md
requires: []
links: ["skill-key-findings-8d4ee09083"]
---

## TL;DR

- Okta Workflows' biggest production traps for an Entra → Okta sync are **silent type/case
  sensitivity** in comparison and Tables cards, **hard record caps that differ per card** (Tables
  Search Rows caps at 3,500 rows; Azure AD Search Groups at 4,000; Azure AD Search Group Members at
  900), and **asynchronous concurrency that floods downstream API rate limits** — all have concrete,
  documented workarounds below.
- The single most important architectural rule: **never do bulk/looping work synchronously in a
  parent flow** — use "Stream Matching Records" or "For Each - Ignore Errors" with a bounded
  `concurrency` value (1–10) into helper flows, and remember **streamed flows cannot be stopped once
  started** (deactivating the flow does not halt an in-progress stream).
- All four of the user's calibration quirks are confirmed and expanded, plus approximately 30
  additional documented quirks across branching, loops, Tables, hooks/streaming, connectors,
  execution limits, error handling, and flopack deployment.
