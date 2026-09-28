---
id: skill-toolchain-recommendations-6b1cdf3505
purpose: toolchain recommendations
source: src/vibey_tools/skills/plugins/writing-craft/skills/white-paper-writing/SKILL.md
requires: ["skill-formatting-and-length-specifications-c21b42a022"]
links: []
---

## Toolchain recommendations

**Academic/technical**: LaTeX (Overleaf for collaboration) — precise typesetting, automated cross-referencing, BibLaTeX for citations. Essential packages: `geometry`, `hyperref`, `biblatex`, `booktabs`, `cleveref`.

**Corporate**: Word + Styles system for consistent formatting and auto-generated TOC. Export to PDF. For highly designed versions, Adobe InDesign or Affinity Publisher.

**Version-controlled technical writing**: Markdown + Pandoc + Git. Write in Markdown (one sentence per line for clean diffs), use YAML front matter for metadata, compile to PDF/DOCX via Pandoc with `--citeproc` for citations.

**Citation management**: Zotero (free, open-source, best browser capture) for most users; BibLaTeX/Biber for LaTeX workflows; EndNote for large-scale systematic reviews with institutional licenses.
