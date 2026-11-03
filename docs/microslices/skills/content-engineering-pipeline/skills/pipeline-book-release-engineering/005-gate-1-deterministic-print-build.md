---
id: skill-gate-1-deterministic-print-build-220664ec11
purpose: gate 1 deterministic print build
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-0-5-release-readiness-contract-4dbe9671af"]
links: ["skill-gate-2-covers-from-the-final-interior-c8a8623813"]
---

## Gate 1: deterministic print build

Build the print interior from the audited source and run the checks against the
finished PDF, not only against the generated TeX. At minimum measure:

- trim size, page count, embedded fonts, annotations, links, transparency,
  margins, gutter rule, and overfull boxes;
- printed folios and every contents entry, including back matter and the author
  page;
- absence of unfinished markers, forbidden dash characters, stale edition
  labels, and development/proof language;
- chapter numbering and the deliberate distinction between numbered narrative
  chapters and unnumbered scholarly back matter;
- the copyright edition line and configured metadata.

If the build produces a PDF with a different page count after a content change,
the old cover and any page-numbered contents evidence are stale. Do not repair
the old artifact by hand. Rebuild the dependent steps.

Use `SOURCE_DATE_EPOCH` or an equivalent stable metadata strategy where the
toolchain supports it. Rebuilding unchanged source should not create a binary
diff merely because a clock moved.
