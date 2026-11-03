---
id: skill-gate-3-epub-build-and-validation-7bc1110f96
purpose: gate 3 epub build and validation
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-2-covers-from-the-final-interior-c8a8623813"]
links: ["skill-gate-4-all-page-visual-evidence-835aa8f0f9"]
---

## Gate 3: EPUB build and validation

Build the EPUB only after the cover exists. Validate both the package and the
reading experience:

- `mimetype` is first and uncompressed;
- XML/XHTML/OPF/NCX are well formed and contain no forbidden entity tricks;
- the visible contents page, EPUB 3 navigation document, and NCX agree on
  labels, nesting, and targets;
- each contents link lands on the heading element that survives conversion;
- the contents landmark points to the visible contents page, while the body
  matter landmark starts the reading order;
- internal links resolve and no stylesheet hides a contents target;
- the cover is an RGB JPEG of the configured minimum size and is declared as
  the package cover without an extra HTML cover page;
- empty paragraphs, empty titles, stale proof language, straight quotes, and
  unfinished markers are absent;
- `epubcheck` runs when installed; if unavailable, the report says so rather
  than implying that the built-in checks are the same thing;
- the final ZIP passes a byte-level integrity test.

The EPUB 3 navigation specification and [EPUBCheck](https://github.com/w3c/epubcheck)
are external validation references. Store-specific converters are additional
acceptance environments, not substitutes for a valid EPUB package; test them
when the target retailer supplies a converter or previewer.
