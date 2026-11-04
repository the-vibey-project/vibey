---
id: skill-the-per-unit-manifest-0dfb94338d
purpose: the per unit manifest
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-serial-fiction-production/SKILL.md
requires: ["skill-the-governing-rule-one-source-every-other-file-derived-6ecce3a212"]
links: ["skill-computed-facts-bb6216686c"]
---

## The per-unit manifest

Whatever varies per unit and is not prose (the date, computed numbers, a
cabin temperature, a print time, a form name, an attachment flag) is recorded in
one machine-readable manifest that the generator reads. A driver that sets those
per batch in a shell script, or a scratch directory, is invisible manual state:
the next person cannot regenerate a single unit.

When the manifest does not exist yet, **bootstrap it from the committed
output**, then run the drift check. That is the cheapest audit available. In the
worked example it showed that most units reproduced exactly, that two had been
edited by hand outside the generator, and that one unit still printed an old
form that every later unit had moved past.
