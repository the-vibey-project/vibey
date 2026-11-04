---
id: skill-determinism-across-machines-16872cc4bc
purpose: determinism across machines
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-serial-fiction-production/SKILL.md
requires: ["skill-the-batch-loop-2dd20e9856"]
links: ["skill-retrospective-lessons-made-executable-da1e7b396b"]
---

## Determinism across machines

A build that passes on the author's machine and fails on the CI runner has not
been engineered. Vendor anything whose packaging varies by distribution (in the
worked example, one TeX distribution shipped a font family in two packages and
the other in one, which stopped every book until the fonts were committed with
their licences and loaded by path). Pin dates. Compare page text, not bytes,
because a document ID legitimately changes with a font path. State in the
repository why each choice was made.
