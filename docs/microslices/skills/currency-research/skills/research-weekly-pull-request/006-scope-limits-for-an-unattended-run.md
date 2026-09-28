---
id: skill-scope-limits-for-an-unattended-run-b663436ebf
purpose: scope limits for an unattended run
source: src/vibey_tools/skills/plugins/currency-research/skills/research-weekly-pull-request/SKILL.md
requires: ["skill-weekly-currency-audit-date-88aa01c4a3"]
links: ["skill-failure-and-partial-results-ef85a0d054"]
---

## Scope limits for an unattended run

An unattended job has no judgement in the loop, so it operates inside hard limits.

**Do:**
- edit only the plugins named in the run's rotation slice;
- keep to a handful of edits — if a run wants more than roughly five, it has misunderstood
  its job and should raise the rest as "Unresolved" instead;
- change the smallest span of text that makes the claim correct;
- leave the pull request in draft if any edit is uncertain.

**Do not:**
- restructure, re-split, rename, add or delete skills or plugins;
- renumber sections, or reflow text that did not need to change;
- touch the release machinery, workflows, `pyproject.toml`, or the package version;
- merge the pull request, or push to `main` or `develop` directly;
- use a repository CLI or API for anything beyond creating and describing the pull
  request — no merging, closing, approving, releasing or changing settings, even when
  the credentials would allow it;
- edit a plugin the slice did not name, however tempting.

⚠️ **The three things that must never happen**, in order of severity:

1. **A fabricated source.** A citation that does not resolve, or a figure attributed to a
   document that does not contain it. This poisons the whole reference and is unrecoverable
   by review, because reviewers check the plausible-looking ones least.
2. **A silent change.** Any edit not described in the pull request body.
3. **A deletion of inconvenient evidence.** Hedging, error bars, dissenting sources and
   "sources disagree" notes are the most valuable content in these documents and the easiest
   to quietly lose while "updating" a section.

---
