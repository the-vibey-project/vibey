---
id: skill-the-governing-rule-no-invisible-manual-state-a90d84f9d7
purpose: the governing rule no invisible manual state
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: []
links: ["skill-release-graph-45a35465c1"]
---

## The governing rule: no invisible manual state

If a future release depends on a command someone remembers, a page someone
looked at once, a word count someone calculated in a one-off shell expression,
or a cover decision that exists only in chat history, the process is not yet
engineered. Convert that decision into one of four durable forms:

1. **Source configuration** — a machine-readable threshold, ordering rule,
   required apparatus list, or exception with a named reason.
2. **Executable gate** — a check that fails with a path, line, artifact, or
   measured value rather than a vague assertion.
3. **Review surface** — a rendered page, contact sheet, EPUB inspection set,
   or report that lets a human make the remaining judgment quickly.
4. **Evidence record** — a versioned JSON manifest containing the source
   revision, commands, tool versions, hashes, counts, warnings, and decisions.

Do not turn a judgment into a fake Boolean merely to make a dashboard green.
Record it as an explicit human decision attached to the evidence bundle.
