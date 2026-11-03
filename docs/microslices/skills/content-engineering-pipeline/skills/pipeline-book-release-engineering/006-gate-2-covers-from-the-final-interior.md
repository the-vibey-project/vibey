---
id: skill-gate-2-covers-from-the-final-interior-c8a8623813
purpose: gate 2 covers from the final interior
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-1-deterministic-print-build-220664ec11"]
links: ["skill-gate-3-epub-build-and-validation-7bc1110f96"]
---

## Gate 2: covers from the final interior

Generate the ebook front cover and print wraps only after every configured
interior page count is final. The cover gate should verify:

- exact ebook, paperback, and hardcover dimensions from the configured trim,
  paper, bleed, board, hinge, and spine rules;
- barcode clearance, text-safe areas, minimum print type size, and panel
  boundaries;
- title/author metadata agreement with the interior;
- each print spine is calculated from its matching format variant, including a
  hardcover page-limit check before artwork is accepted;
- readable typography over artwork at the actual cover scale;
- deterministic artwork from a declared seed and bundled fonts/assets;
- the presence of every required upload file, including one-page wrap PDFs.

The script can prove geometry and pixel placement. It cannot prove that the
cover is sexy, beautiful, or appropriate to the book. Produce a front-cover
preview and a print-wrap preview as a review surface, then record the human
decision in the release manifest.
