---
id: skill-gate-0-source-and-manuscript-audit-e7687b5dfd
purpose: gate 0 source and manuscript audit
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-release-graph-45a35465c1"]
links: ["skill-gate-0-5-release-readiness-contract-4dbe9671af"]
---

## Gate 0: source and manuscript audit

Before invoking a TeX engine, audit the source of record. The audit should:

- load the one book configuration and verify that every Markdown file is
  printed, deliberately excluded, or reported as an error;
- reject missing, duplicate, empty, or untitled entries;
- count words by front matter, numbered chapter, and back matter, with the
  counting basis stated in the report;
- enforce the target, hard floor, chapter count, shortest-chapter floor, and
  permitted chapter-imbalance ratio declared by the author;
- verify that required research method, source guide, evidence, objections,
  institutional, and bibliography pieces are present and carry their actual
  reader-facing titles;
- reject unfinished markers and high-confidence planning language such as
  “Evidence packet:” or “Case study:” when those phrases are not part of the
  book's intended prose;
- require numbered chapter openings to begin with an uppercase letter when the
  print design uses a drop cap, and report later lowercase paragraph openings as
  editorial warnings unless the book opts into a stricter gate;
- count repeated rhetorical formulas so the sentence-level pass can see when a
  useful contrast has become a template;
- distinguish hard failures from warnings and preserve both in JSON.

A word-count target is not permission to pad. If the target is missed, the
report should identify the gap and the shortest chapters so the next pass adds
evidence, mechanism, case study, objection, or theological development. The
quality gate must not reward repeated claims that add no new knowledge.
