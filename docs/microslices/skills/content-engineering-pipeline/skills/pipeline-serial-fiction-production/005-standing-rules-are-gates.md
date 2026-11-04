---
id: skill-standing-rules-are-gates-8680a34756
purpose: standing rules are gates
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-serial-fiction-production/SKILL.md
requires: ["skill-canon-is-searched-before-it-is-written-40f81ac2cd"]
links: ["skill-found-document-forms-823f666858"]
---

## Standing rules are gates

Rules the author states in conversation (banned characters and words, no
scaffolding the reader would see, which characters appear in every unit, no
contact details, how a faith or a name is handled) are written into a linter in
the repository the first time they are stated, with tests that each rule catches
what it names.

- Run it on **every** volume. A volume that predates a rule reports its legacy
  hits as warnings, with a `--strict` switch, so the policy is explicit rather
  than accidental.
- Lint the writing map and the manifest as well as the prose: they are source
  too, and the first unescaped character in a note stops the document that
  renders them.
- A frame break (a planning label such as a chapter code, or a reference to the
  book's own structure from inside it) is an error in every unit. In the worked
  example the linter found one in the 82nd unit that every human pass had missed.

Prose-level canon (who believes what, who reads which text) cannot be linted.
It belongs in the writing map and the decision log, and in the search before
drafting.
