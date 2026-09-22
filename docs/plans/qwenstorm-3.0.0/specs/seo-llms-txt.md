## Title
feat(docs): generate `docs/llms.txt`, the LLM-crawler index, from `properdocs.yml`'s own nav

## Why
There is no `llms.txt` anywhere in the repository (`find . -iname 'llms*.txt'` is empty).
`llms.txt` is an emerging, now widely-adopted convention (llmstxt.org) for a plain-markdown
index that an LLM/RAG pipeline reads instead of crawling and rendering an entire HTML site:
an H1 project name, a one-line blockquote summary, then H2-grouped links to the pages that
matter, with an "Optional" section for material a quick answer can skip. Vibey ships
extensive documentation (`properdocs.yml`'s `nav:` lists 6 guides, 2 reference pages, and
44 ADRs) with no equivalent single entry point for a crawler that cannot or will not run a
full site crawl.

Sub-doctrine 12.c requires this to be declared and reconciled from the repository, not
hand-authored prose that drifts the first time a guide is added or an ADR lands — `nav:`
in `properdocs.yml` is already the single source of truth for what the site contains and
in what order (used identically by `tests/meta/test_adr_counts.py`-style checks
elsewhere in this repository), so `llms.txt` must be generated from it, not maintained
by hand a second time.

`llms-full.txt` (the companion "everything concatenated" convention) is deliberately
**not** added here: ADR-0032 already ships exactly that artifact under a different name —
`book-print.html` (plus the PDF/EPUB) is "every page of the documentation site, in reading
order, as one downloadable book" (`README.md:296`). A third parallel full-text format
would be a second thing to keep in sync with the same content for no discovery benefit;
`llms.txt`'s own "Optional" section instead points a full-context crawler at the book.

## Required behaviour
1. Create `scripts/generate_llms_txt.py` (module-level functions, matching
   `scripts/paper_evidence.py`'s shape) with:
   - `render(properdocs_path: Path, readme_path: Path) -> str`: parses `properdocs.yml`
     with `yaml.safe_load` for `site_name`, `site_url`, and `nav`; parses `readme_path`
     for the first `**Vibey is the layer that does the babysitting.**` paragraph
     (`README.md:20-25`) as the one-line summary (strip markdown emphasis markers); walks
     `nav` and renders:
     ```
     # vibey

     > <the one-line summary, plain text, no markdown emphasis>

     ## Docs

     - [<nav title>](<site_url><relative path with .md replaced by nothing, matching mkdocs's own URL scheme>): <first sentence of that page's own first paragraph, if the page front-matters one; otherwise omit the colon and description>

     ## Reference

     - [CLI reference](<site_url>reference/cli/)
     - [Configuration reference](<site_url>reference/configuration/)

     ## Optional

     - [Research paper (PDF)](https://the-vibey-project.github.io/vibey/main/paper.pdf)
     - [The complete documentation as one book (PDF)](https://the-vibey-project.github.io/vibey/main/book.pdf)
     - [Every architecture decision (44 ADRs)](<site_url>architecture/decisions/)
     - [Source repository](https://github.com/the-vibey-project/vibey)
     ```
     Group nav entries under `## Docs` for everything under "Guides", and put
     "Reference" and "Architecture: Decision records" into their own named sections
     mirroring `nav`'s own top-level grouping — do not flatten every nav entry into one
     list; the H2 grouping is the point of the format.
   - `main(argv: list[str] | None = None) -> int`: `argparse` with one flag, `--check`.
     Without `--check`, writes the rendered text to `docs/llms.txt`. With `--check`,
     renders in memory and exits 1 with a diff-style message if `docs/llms.txt` does not
     already match, 0 if it does — the same generate-then-verify shape
     `vibey-gh corpus-index --check` and `vibey-gh marketplace`/`vibey-gh check` already
     use elsewhere in this family (ADR-0017: dogfood the shape, don't invent a new one).
2. Run `python3 scripts/generate_llms_txt.py` once and commit the resulting
   `docs/llms.txt`. Because it is a `.txt` file (not `.md`) inside `docs/`, mkdocs/
   properdocs copies it through to the built site unchanged at `site/llms.txt`
   (`properdocs.yml` has no `exclude_docs` entry that would catch it — its one
   `exclude_docs: plans/**` does not match `llms.txt`).
3. New `tests/meta/test_llms_txt_is_current.py` asserting `generate_llms_txt.main(["--check"])`
   returns 0 against the committed file, so a future doc addition that is not reflected
   here fails CI loudly rather than silently going stale.

## Where to change
- Create `scripts/generate_llms_txt.py`.
- Create `docs/llms.txt` (generated output — do not hand-edit after generating it).
- Create `tests/meta/test_llms_txt_is_current.py`. Copy the provenance header from
  `tests/meta/test_adr_counts.py:1`.

## Acceptance criteria
- [ ] `docs/llms.txt` exists, starts with `# vibey`, and its second non-blank line is a
      `>`-prefixed one-line summary.
- [ ] It has at least three `## `-headed sections, and an `## Optional` section whose
      links include the paper PDF and the book PDF (not a third concatenated-text
      artifact).
- [ ] `python3 scripts/generate_llms_txt.py --check` exits 0.
- [ ] Every URL in `docs/llms.txt` that points at `the-vibey-project.github.io/vibey`
      corresponds to a real `nav` entry in `properdocs.yml` or one of the two fixed
      reference pages.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_llms_txt_is_current.py` passes.

## Tests to write first (TDD)
`tests/meta/test_llms_txt_is_current.py`:
- `test_llms_txt_matches_generator_output`: call `main(["--check"])`; assert return value 0.
- `test_render_includes_every_top_level_nav_section`: parse `properdocs.yml`'s `nav` and
  assert `render(...)` contains an `## ` heading for each top-level nav group name (Home
  is folded into the summary, not its own section).
- `test_render_is_pure_ascii_markdown_no_html`: guards against a stray HTML tag leaking
  in from a badly-stripped markdown emphasis marker.
- `test_check_flag_fails_on_a_stale_file`: write a deliberately wrong `docs/llms.txt` to
  a tmp_path copy and assert `--check` reports non-zero.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    python3 scripts/generate_llms_txt.py --check
    uv run pytest -q -p no:cacheprovider tests/meta/test_llms_txt_is_current.py

## Out of scope
- `llms-full.txt` — deliberately not added; see Why. If the operator later decides the
  book is not an adequate substitute, that is a new decision for a new lane, not a
  silent addition here.
- Wiring `--check` into a permanent CI job (today nothing in `ci.yml` builds the root
  docs site at all — see `seo-docs-structured-data`'s Why for the same observation).
  This lane's own test is the regression guard; adding a CI step is a natural follow-up
  but a separate, larger change to `ci.yml`.
- Per-page descriptions beyond the first-paragraph heuristic — if a page has no usable
  first paragraph (e.g. it opens with a table or code block), omit the colon and
  description for that entry rather than inventing one.
- `README.md`, pyproject.toml, and every other file in this SEO/LEO wave.

Commit as `feat(docs): generate docs/llms.txt from properdocs.yml's nav`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
