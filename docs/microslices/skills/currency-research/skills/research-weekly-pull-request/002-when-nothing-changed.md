---
id: skill-when-nothing-changed-3430f94e37
purpose: when nothing changed
source: src/vibey_tools/skills/plugins/currency-research/skills/research-weekly-pull-request/SKILL.md
requires: ["skill-the-reviewer-is-the-constraint-48a2d90407"]
links: ["skill-branch-and-commit-bdefcd18d1"]
---

## When nothing changed

**Do not open a pull request.** A no-change run is the expected outcome and it should be
silent in the repository's history.

Report the result where the run is visible instead — the job summary, or a comment on an
existing tracking issue if the workflow provides one. Say which plugins were audited, which
claims were checked, and what sources were consulted. That record is what stops the next run
from repeating identical searches with no memory.

⚠️ **Never open an empty or cosmetic pull request to demonstrate that the job ran.** The job's
own logs demonstrate that.

---
