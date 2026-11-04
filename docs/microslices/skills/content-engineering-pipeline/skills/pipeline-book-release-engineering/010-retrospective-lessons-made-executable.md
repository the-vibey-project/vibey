---
id: skill-retrospective-lessons-made-executable-d2068f6822
purpose: retrospective lessons made executable
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-5-release-manifest-4be09ecb53"]
links: ["skill-operating-procedure-96e9c803c0"]
---

## Retrospective lessons made executable

The following failure patterns are release regressions and should remain
covered by tests:

| Manual discovery | Durable gate |
| --- | --- |
| A page-specific lowercase opening broke a drop cap | audit every numbered chapter opening |
| A fragment such as “retrieval.” reached a printed page | configurable paragraph-start lint |
| Planning packets appeared as prose | forbidden scaffold phrases and markers |
| Back matter changed from a research apparatus to a bibliography | required actual back-matter titles |
| Numbered chapters and scholarly back matter became mixed | source model and PDF/EPUB ToC checks |
| Cover text disappeared into artwork | cover safe-area, pixel, and preview checks |
| A PDF page count changed the spine | PDF → cover dependency order |
| A compact hardcover used the paperback page count | format matrix and per-variant spine input |
| EPUB was refreshed manually after a merge | one release command plus deterministic timestamps |
| Every page was “checked” from memory | page-counted renders, contact sheets, and report |
| A build passed without `epubcheck` | explicit unavailable-tool status |
| Store metadata and pricing were decided in a launch conversation | release-readiness contract with metadata, keyword, research, dated-source, and unit-economics checks |
| A long book was priced as a hardcover without checking the retailer limit | page-count feasibility gate and explicit external-provider or split-edition decision |
| Every book's PDF build failed in CI for several merges, because the runner's TeX packaging omitted a font the author's machine had | interior fonts vendored with their licences and loaded by path; one set of font files decides line breaks and page counts |
| The release workflow had been red on every push and nobody had looked at the run history | read the workflow's recent runs before adding a gate; a red check is a finding, not background |
| Unit tests existed and CI never ran them | tests run as the first workflow step, before the heavy build |

These gates do not eliminate editing. They make editing honest: the machine
handles inventory, measurement, conversion, and evidence; the author handles
meaning, beauty, historical judgment, and the final decision to put a name on
the work.
