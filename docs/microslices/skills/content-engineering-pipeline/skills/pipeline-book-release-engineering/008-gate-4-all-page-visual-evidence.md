---
id: skill-gate-4-all-page-visual-evidence-835aa8f0f9
purpose: gate 4 all page visual evidence
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-3-epub-build-and-validation-7bc1110f96"]
links: ["skill-gate-5-release-manifest-4be09ecb53"]
---

## Gate 4: all-page visual evidence

Render every PDF page at a declared DPI. Do not render only the page that was
reported in a conversation: typography failures migrate when pagination
changes. The renderer should:

- produce one numbered PNG per physical page and fail if the count differs;
- assemble contact sheets with visible page labels and a stable order;
- record dimensions, file sizes, blank pages, and overlong blank runs;
- preserve the individual pages for close inspection of drop caps, chapter
  openers, folios, contents, bibliography, tables, cover previews, and any
  previously repaired page;
- distinguish intentional structural blank pages from an unexpected run,
  using the same rule as the print validator;
- write the render report beside the release report.

The render report proves coverage, not taste. A human must still inspect the
contact sheets and sample pages at reading scale. The human review should be a
recorded decision with the report's artifact hash, not an untraceable “looked
good” in chat.
