* **`vibey design accept --spec-json` keeps the research gaps:** an imported spec was built
  without `research_gaps`, so editing a synthesized spec and importing it silently dropped the
  "Research not performed" section, although the field exists so that "the spec states every
  gap". The loader now reads an optional `research_gaps` list of `{topic, reason}`, refusing a
  gap with no topic or no reason, and the documented shape says to keep them when editing.
