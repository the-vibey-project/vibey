---
id: skill-failure-and-partial-results-470445eadf
purpose: failure and partial results
source: src/vibey_tools/skills/plugins/currency-research/skills/research-weekly-pull-request/SKILL.md
requires: ["skill-scope-limits-for-an-unattended-run-8f24808388"]
links: []
---

## Failure and partial results

- If a search tool or the network is unavailable, **stop and report it.** Do not fall back to
  recalled knowledge — see `research-search-and-source-quality`.
- If the repository's checkers fail on your edit, fix it or drop that edit. Never open a
  pull request that is known to fail CI.
- If the run is interrupted, **an incomplete audit that says which plugins it got through is
  fine.** A complete-looking audit that silently skipped half its slice is not.
