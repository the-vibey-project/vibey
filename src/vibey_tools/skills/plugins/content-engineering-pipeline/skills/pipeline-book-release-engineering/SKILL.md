---
name: pipeline-book-release-engineering
description: "Use when taking a research-based manuscript from a locked draft to reproducible PDF, EPUB, cover, and release evidence; triggers on book publication, print interiors, ebook packaging, cover generation, visual QA, KDP preparation, artifact manifests, or postmortems of a manual publishing workflow."
---

# Book Release Engineering

Book production is a software delivery problem with a human editorial
acceptance layer. A manuscript is source code, a book configuration is a build
manifest, the PDF/EPUB/covers are compiled artifacts, and the release report is
the evidence that the artifacts came from the intended source and passed the
declared gates. The analogy is useful only if it preserves the difference:
typesetting can be deterministic while literary judgment remains human.

This skill is the reusable release layer for the Content Engineering Pipeline's
Phases 4–5. It closes the gap between a publication method that describes what
should be checked and a repository that can prove what was checked. Use it
after the manuscript's structural, argument, consistency, voice, evidence, and
placeholder passes are complete, and before any store submission or public
distribution.

## The governing rule: no invisible manual state

If a future release depends on a command someone remembers, a page someone
looked at once, a word count someone calculated in a one-off shell expression,
or a cover decision that exists only in chat history, the process is not yet
engineered. Convert that decision into one of four durable forms:

1. **Source configuration** — a machine-readable threshold, ordering rule,
   required apparatus list, or exception with a named reason.
2. **Executable gate** — a check that fails with a path, line, artifact, or
   measured value rather than a vague assertion.
3. **Review surface** — a rendered page, contact sheet, EPUB inspection set,
   or report that lets a human make the remaining judgment quickly.
4. **Evidence record** — a versioned JSON manifest containing the source
   revision, commands, tool versions, hashes, counts, warnings, and decisions.

Do not turn a judgment into a fake Boolean merely to make a dashboard green.
Record it as an explicit human decision attached to the evidence bundle.

## Release graph

The release command must own this dependency graph:

```text
source inventory and prose audit
        │
        ▼
release-readiness contract ──► metadata, research, pricing, format feasibility
        │
        ▼
print interior ──► PDF structural and folio checks
        │
        ▼
cover geometry/art ──► cover safe-area and legibility checks
        │
        ▼
reflowable EPUB ──► EPUB structure, navigation, links, and ZIP checks
        │
        ▼
all-page rendering ──► contact sheets and human visual review
        │
        ▼
release manifest ──► author approval and distribution handoff
```

When a title has more than one print interior, make the format matrix part of
the book configuration before building:

```text
locked source
   ├── standard interior ──► paperback cover geometry
   └── compact hardcover interior ──► hardcover cover geometry
   └── EPUB ──► ebook cover
```

Each interior is a format variant of the same source, never a manually edited
copy. The release manifest must record each variant's PDF path, page count,
hash, render report, and configured page-limit policy. A cover spine must read
the page count from the matching final interior; using the standard PDF's page
count for a compact hardcover is a release defect.

The order is load-bearing. A cover cannot know its print spine until the PDF
page count is final. An EPUB cannot embed its cover until the cover exists. A
table of contents cannot be trusted until typesetting has settled. A visual
review cannot be attached to the release until the exact artifact has been
rendered. Never parallelize these steps merely because the tools are available.

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

## Gate 0.5: release-readiness contract

Before spending time on typesetting, verify the commercial and evidentiary
inputs that were previously likely to live in a spreadsheet, a launch note, or
the operator's memory. The book configuration is the source of record. A
release contract should declare and the native publisher command should measure:

- title, subtitle, author, description, and the description's minimum useful
  length;
- the exact store-keyword count required by the target retailer, with unique,
  non-empty keywords and no accidental duplication;
- the required research apparatus files and a minimum count of reader-facing
  source URLs, so a researched book cannot pass after its evidence register was
  omitted from the build;
- the date, source URL, currency, list prices, royalty assumptions, delivery
  costs, and print-cost assumptions used for the pricing decision;
- estimated unit economics for every configured format, reported as evidence
  rather than treated as a promise of retailer payout;
- page-count and trim constraints for each retailer and format. If a book
  exceeds a platform limit, the contract must disable that format for that
  platform or name the external provider and variant that will carry it.

The gate must fail on missing metadata, an invalid keyword cardinality, missing
research apparatus, absent or stale pricing verification, impossible prices,
or a configured format whose page count cannot be accepted by its retailer. It
may warn on a deliberate alternative such as an external hardcover provider,
but that warning must be explicit in the machine-readable report. The report
must be written beside the other release evidence before the build continues.

This gate is intentionally separate from human approval. A machine can prove
that seven keywords exist, that a pricing source was checked on a stated date,
and that a 607-page interior exceeds a 550-page KDP hardcover limit. It cannot
decide whether the positioning is honest, whether the price is wise, or whether
the final cover deserves approval. Those remain recorded human judgments.

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

## Gate 5: release manifest

Write one machine-readable manifest for the exact release attempt. A minimal
manifest contains:

```json
{
  "schema_version": 1,
  "source": {"git_commit": "...", "config": "books/example.toml"},
  "manuscript": {"word_count": 0, "chapters": 0, "warnings": []},
  "steps": [{"name": "pdf", "status": "pass", "command": []}],
  "artifacts": [
    {"kind": "pdf-interior", "path": "output/example.pdf", "sha256": "..."},
    {"kind": "epub", "path": "output/example.epub", "sha256": "..."}
  ],
  "visual_qa": {"page_count": 0, "rendered_pages": 0, "contact_sheets": []},
  "human_review": {"status": "pending", "reviewer": null, "notes": []}
}
```

The manifest is not a marketing document. It is a chain of custody. If the
branch changes, a merge conflict is resolved, or any source file changes after
the report, the old manifest is evidence for the old release attempt and must
not be reused. Rerun the complete graph and issue a new manifest.

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

## Operating procedure

1. Lock the manuscript and configuration; do not begin from an old output file.
2. Run the source audit and resolve every hard failure. Read warnings as a
   revision queue, not as decoration.
3. Run the release-readiness contract and resolve every hard failure or record
   the explicit platform/format exception.
4. Build PDF, cover, and EPUB in dependency order.
5. Render every page and inspect the contact sheets and representative full-size
   pages. Record human review.
6. Run the external retailer/previewer checks available for the intended format.
7. Write the manifest, compare artifact hashes to the reviewed files, and only
   then prepare the distribution handoff.
8. If a conflict, content edit, metadata edit, page repair, or cover repair
   occurs, invalidate the old manifest and rerun from Gate 0.

For repositories with a native command, use that command rather than copying
this sequence into a shell. In engineering-influence the canonical entry point
is `scripts/publish_book.py`; the skill supplies the method, while the
repository owns the implementation details and thresholds.

## References

- [EPUB 3.3](https://www.w3.org/TR/epub-33/) — package, navigation, and reading-order requirements.
- [EPUBCheck](https://github.com/w3c/epubcheck) — reference EPUB conformance validator.
- [SOURCE_DATE_EPOCH](https://reproducible-builds.org/docs/source-date-epoch/) — reproducible-build timestamp convention.
- [Content Engineering Pipeline: Book Production](../pipeline-book-production/SKILL.md) — Phase 4 assembly and Phase 5 revision gates that precede this release layer.
