---
id: skill-byte-discipline-325139ec26
purpose: byte discipline
source: src/vibey_tools/skills/plugins/currency-research/skills/research-editing-a-reference-skill/SKILL.md
requires: ["skill-the-cross-reference-rule-a7168b3a36"]
links: ["skill-what-else-must-change-when-you-edit-a5ea2fb306"]
---

## Byte discipline

The section bodies are byte-identical to the source documents they were split from, and
tooling checks that. So:

- **Change only the characters that must change.** Do not reflow paragraphs, normalise
  punctuation, convert quotes, retab tables or "tidy" whitespace.
- **Keep the line wrapping style of the surrounding text.** These files are hand-wrapped at
  roughly 90 characters; a re-wrapped paragraph produces an enormous, unreviewable diff for a
  one-word change.
- **Preserve the markers.** The ⚠️ prefixes, the bold runs, the confidence tags and the table
  shapes are all deliberate.
- **Do not renumber sections.** Ever, in a currency edit. Numbering is shared across the
  plugin, cited by sibling skills and sometimes cited by *other* plugins.

---
