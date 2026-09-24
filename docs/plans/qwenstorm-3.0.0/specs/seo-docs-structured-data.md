## Title
feat(docs): inject per-page meta description, canonical link, Open Graph/Twitter Card tags, and schema.org JSON-LD into the built docs site

## Why
The docs site is built by `properdocs` (`pip install properdocs==1.6.7
properdocs-theme-mkdocs==1.6.7 && properdocs build --strict`,
`.github/workflows/release-surfaces.yml`), configured by `properdocs.yml` with
`theme: mkdocs` — the vanilla base theme, not a themed fork with SEO extras. That base
theme emits no `<meta property="og:...">`, no `<meta name="twitter:...">`, no
`<link rel="canonical">`, no schema.org structured data, and no per-page
`<meta name="description">` distinct from the one site-wide `site_description=` in
`properdocs.yml` — confirmed by `properdocs.yml` having no `plugins:` entry beyond
`search` and no `theme: {custom_dir: ...}` override. Every one of those is exactly what
a search engine's rich-result renderer and a social-link unfurler (Slack, Twitter/X,
LinkedIn, Discord) reads, and what a RAG pipeline's chunker uses to attribute a page to
a topic before ever reading its body. Today, sharing any page of
`https://the-vibey-project.github.io/vibey/main/` produces a bare link with no preview.

Rather than depend on `properdocs`'s internal template-extension surface (undocumented
from this checkout — the package is not vendored here, and this repository pins it as
an external dependency installed fresh in CI), this lane post-processes the tool's own
static HTML output. That is guaranteed to work regardless of what `properdocs` does or
does not expose as a customization point, and it keeps the fix in one small, fully
unit-testable script rather than a fragile theme override.

## Required behaviour
1. Create `scripts/inject_docs_meta.py` (module-level functions, matching
   `scripts/paper_evidence.py`'s shape) with:
   - `load_site_config(properdocs_yml: Path) -> SiteConfig`: reads `site_name`,
     `site_description`, `site_url` with `yaml.safe_load`.
   - `page_description(html: str, fallback: str) -> str`: the text content of the first
     `<p>` element after the first `<h1>`, collapsed to single spaces, truncated to 155
     characters at the last word boundary with a trailing `…` if truncated; `fallback`
     (the site description) if no such `<p>` exists.
   - `canonical_url(site_url: str, site_relative_path: str) -> str`: `site_url` (with
     exactly one trailing slash) joined with the page's path relative to the site root,
     with a bare `index.html` mapped to its directory (mkdocs's own directory-URL
     convention: `reference/cli/index.html` → `reference/cli/`; root `index.html` → `""`).
   - `inject(html: str, *, title: str, description: str, canonical: str, site_name: str,
     image_url: str, json_ld: str | None) -> str`: returns `html` with these elements
     inserted immediately before `</head>` (a no-op, returning `html` unchanged, for any
     tag that is already present — checked by a literal substring match on the tag's
     `name=`/`property=`/`rel=` attribute, so re-running the script is idempotent):
     ```html
     <meta name="description" content="{description}">
     <link rel="canonical" href="{canonical}">
     <meta property="og:title" content="{title}">
     <meta property="og:description" content="{description}">
     <meta property="og:type" content="website">
     <meta property="og:url" content="{canonical}">
     <meta property="og:site_name" content="{site_name}">
     <meta property="og:image" content="{image_url}">
     <meta name="twitter:card" content="summary_large_image">
     <meta name="twitter:title" content="{title}">
     <meta name="twitter:description" content="{description}">
     <meta name="twitter:image" content="{image_url}">
     ```
     followed by `<script type="application/ld+json">{json_ld}</script>` when `json_ld`
     is not `None`.
   - `homepage_json_ld(site_url: str, description: str) -> str`: a `json.dumps` of
     ```json
     {
       "@context": "https://schema.org",
       "@type": "SoftwareApplication",
       "name": "vibey",
       "description": "<description>",
       "url": "<site_url>",
       "applicationCategory": "DeveloperApplication",
       "operatingSystem": "Linux, macOS",
       "license": "https://github.com/the-vibey-project/vibey/blob/main/LICENSE",
       "codeRepository": "https://github.com/the-vibey-project/vibey",
       "downloadUrl": "https://pypi.org/project/vibey/",
       "programmingLanguage": "Python",
       "author": {"@type": "Person", "name": "Adam Matthew Steinberger", "url": "https://github.com/adammatthewsteinberger"}
     }
     ```
     Deliberately omit `softwareVersion`: a hardcoded version in a static asset goes
     stale the moment the next release ships, which sub-doctrine 10.f treats as a false
     evidence claim, not a convenience.
   - `paper_json_ld(site_url: str) -> str`: a `json.dumps` of a `ScholarlyArticle` with
     `headline` = "Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software
     Delivery over a Pool of Coding Agents", `url` = `f"{site_url}main/paper/"`, `author`
     `{"@type": "Person", "name": "Adam Matthew Steinberger"}`, and `isPartOf`
     `{"@type": "WebSite", "name": "vibey", "url": site_url}`.
   - `main(argv: list[str] | None = None) -> int`: `argparse` with `--site-dir` (default
     `site`) and `--properdocs-yml` (default `properdocs.yml`). Walks
     `Path(site_dir).rglob("*.html")`, computes each file's site-relative path and
     `<title>` (regex on the file's own `<title>...</title>`), calls `inject(...)` with
     `homepage_json_ld(...)` only for the site root's `index.html` and `paper_json_ld(...)`
     only for `main/paper/index.html` or `paper/index.html` (whichever the build actually
     produces — check both), `None` for every other page, and writes the file back.
     `image_url` is `f"{site_url}img/social-preview.png"` for every page (see
     `seo-favicon-social-image`, which lands that file independently as a real raster PNG
     — Open Graph/Twitter unfurlers do not reliably render SVG images, so the favicon and
     the social-card image are deliberately two different files. This script does not
     require the file to exist yet, since it only ever emits a URL string).
2. This is a post-build step: it does not change how `properdocs build` runs, only what
   happens to its `site/` output afterward.

## Where to change
- Create `scripts/inject_docs_meta.py`.
- Create `tests/meta/test_inject_docs_meta.py`. Copy the provenance header from
  `tests/meta/test_adr_counts.py:1`.
- After you have proven the script works (all checks below pass), add ONE line to
  `src/vibey_tools/gh/vibey_gh/templates/workflows/release-surfaces.yml`, directly after
  its `properdocs build --strict` step (find it with
  `grep -n "properdocs build --strict" src/vibey_tools/gh/vibey_gh/templates/workflows/release-surfaces.yml`):
  a new step running `python3 scripts/inject_docs_meta.py --site-dir <the same site-dir
  that step already builds into>`. **Do not** edit
  `.github/workflows/release-surfaces.yml` directly — it is a file `vibey-gh install`
  renders from that template plus `.vibey-gh.toml`, and `tools-lint`'s drift check fails
  a hand-edited copy that no longer matches its own template. After editing the
  template, run `uv run vibey-gh install` (or `python -m vibey_gh install`, whichever
  this checkout's `vibey-gh` exposes) from the repository root to re-render
  `.github/workflows/release-surfaces.yml`, and commit both files together.

## Acceptance criteria
- [ ] `inject()` is idempotent: running it twice on the same HTML produces byte-identical output the second time.
- [ ] Every tag listed in behaviour 1's `inject` block appears in a fixture page after one call.
- [ ] `homepage_json_ld` output is valid JSON (`json.loads` round-trips it) and contains no `softwareVersion` key.
- [ ] `python3 scripts/inject_docs_meta.py --help` exits 0 and documents both flags.
- [ ] `grep -n "inject_docs_meta.py" src/vibey_tools/gh/vibey_gh/templates/workflows/release-surfaces.yml` and the rendered `.github/workflows/release-surfaces.yml` both show the new step, in the same relative position.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_inject_docs_meta.py` passes.

## Tests to write first (TDD)
`tests/meta/test_inject_docs_meta.py`, all against small in-memory or `tmp_path` HTML fixtures (no real `properdocs` build required):
- `test_page_description_takes_first_paragraph_after_h1`.
- `test_page_description_truncates_at_word_boundary_with_ellipsis`.
- `test_page_description_falls_back_to_site_description_with_no_paragraph`.
- `test_canonical_url_maps_index_html_to_its_directory`.
- `test_canonical_url_maps_root_index_html_to_the_bare_site_url`.
- `test_inject_adds_every_required_tag_once`.
- `test_inject_is_idempotent_on_a_second_call`.
- `test_homepage_json_ld_is_valid_json_and_has_no_softwareVersion`.
- `test_paper_json_ld_headline_matches_the_papers_actual_title`: compare against the
  `<title>` mkdocs actually gives the rendered paper page, read from a fixture, not
  hardcoded twice.
- `test_main_walks_every_html_file_under_site_dir`: a small fixture tree with 3 pages;
  assert all 3 got the shared tags and only the homepage got `SoftwareApplication` JSON-LD.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta/test_inject_docs_meta.py
    python3 scripts/inject_docs_meta.py --help

## Out of scope
- The `properdocs.yml`/theme/favicon wiring and the actual image asset — `seo-favicon-social-image`.
- `docs/robots.txt` and verifying `sitemap.xml` — `seo-robots-sitemap`.
- Adding a CI job that builds the root docs site on every PR (today only
  `release-surfaces.yml` builds it, at release time) — a separate, larger change to
  `ci.yml`, not this lane.
- The GitHub repository's own social-preview image (Settings → General → Social
  preview): GitHub exposes no REST/GraphQL endpoint to set it, so it cannot be declared
  as code at all — a recorded exception to 12.c, not a gap this lane can close.
- README.md, pyproject.toml, ADRs, CHANGELOG.md, and CLAUDE.md/AGENTS.md/GEMINI.md.

Commit as `feat(docs): inject OG/Twitter/JSON-LD meta into the built docs site`. Do not push.

## Lane card
- **Depends on:** nothing to build and test the script. The final wiring step touches
  `release-surfaces.yml`'s template, which `seo-robots-sitemap` does not touch (that
  lane ships a plain static file with no template change) — no collision.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
