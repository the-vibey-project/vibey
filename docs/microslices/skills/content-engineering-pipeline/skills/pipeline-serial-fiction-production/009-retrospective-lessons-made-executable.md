---
id: skill-retrospective-lessons-made-executable-da1e7b396b
purpose: retrospective lessons made executable
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-serial-fiction-production/SKILL.md
requires: ["skill-determinism-across-machines-16872cc4bc"]
links: ["skill-operating-procedure-e187a550f6"]
---

## Retrospective lessons made executable

| Manual discovery | Durable gate |
| --- | --- |
| The per-unit header numbers lived in a scratch script | per-unit manifest read by the generator |
| A typeset unit no longer matched its own draft | `--check` at every arrow, run as a unit test |
| A unit was hand-edited outside the generator | bootstrap the manifest from output; the first diff finds it |
| One unit kept an old form every later unit had left | the same drift check, by form |
| A planning label reached a reader | frame-break lint on every unit |
| A banned word survived 17 times in an early volume | rule applied to all volumes; legacy hits are explicit warnings |
| The writing map could not be regenerated, and had gone stale | map composed from its sources; map notes linted for LaTeX safety |
| A second, older copy of a builder diverged | one builder; the old path forwards to it |
| A flash-forward excerpt was reworded in the full record | later documents built from the earlier text and diffed |
| A date moved and three documents kept the old one | the calendar in code; tests pin the values the story needs |
| The decision documents and the text disagreed in silence | dated entries appended and marked open for the author |
| CI never ran the existing tests or the series checks | tests and chain check are the first CI steps |
