---
id: skill-branch-and-commit-bdefcd18d1
purpose: branch and commit
source: src/vibey_tools/skills/plugins/currency-research/skills/research-weekly-pull-request/SKILL.md
requires: ["skill-when-nothing-changed-3430f94e37"]
links: ["skill-the-pull-request-body-3b66f6bf25"]
---

## Branch and commit

- **Branch:** `claude/currency-<ISO date>` — dated, so concurrent or retried runs do not collide.
- **Base:** the repository's integration branch (`develop` here), not `main`.
- **One commit** unless the edits are genuinely independent; a reviewer reading a two-file diff
  does not benefit from five commits.
- **Commit subject:** name the plugins touched and the nature of the change, e.g.
  `Refresh currency claims in semiconductors and wireless (2 plugins)`.
- **Commit body:** one line per edit — what changed, from what to what, and the source.
- **Commit trailer:** every commit carries the repository's fingerprint trailer. It is
  mandatory and enforced in CI, so a commit without it fails the pull request:

  ```
  Made-With: Vibey, the auto-vibecoding machine by Adam Matthew Steinberger
  ```

---
