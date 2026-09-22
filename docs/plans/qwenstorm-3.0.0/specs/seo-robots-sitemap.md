## Title
feat(docs): declare `docs/robots.txt`, and prove the built site still emits `sitemap.xml`

## Why
There is no `robots.txt` anywhere in the repository (`find . -iname 'robots.txt'` is
empty), so the docs site currently ships none — a crawler has no declared policy and no
pointer to the sitemap, which is exactly the kind of thing sub-doctrine 12.c says must
be declared in the repository rather than left to an implicit default.

`sitemap.xml` is different: mkdocs (and, on the evidence of `properdocs.yml`'s
otherwise-identical config surface — `site_name`, `site_url`, `theme`, `plugins`,
`markdown_extensions`, `nav`, `exclude_docs` — `properdocs` too) generates
`sitemap.xml`/`sitemap.xml.gz` automatically for every build whenever `site_url` is set,
with no plugin or config needed; `properdocs.yml:5` already sets
`site_url: https://the-vibey-project.github.io/vibey/`. Nothing in this repository
currently proves that, though — it is an assumption about a pinned third-party
package's behaviour, not a checked fact, and sub-doctrine 10.f treats an unverified
assumption as no better than a missing one. This lane declares the one artifact that
needs declaring (`robots.txt`) and turns the other one from an assumption into a
verified, regression-guarded fact.

## Required behaviour
1. Create `docs/robots.txt`:
   ```
   User-agent: *
   Allow: /

   Sitemap: https://the-vibey-project.github.io/vibey/sitemap.xml
   ```
   Because it is a non-Markdown file under `docs/` (mkdocs's `docs_dir`), properdocs
   copies it through to the built site unchanged at `site/robots.txt` — the same static-
   passthrough mechanism that already carries `docs/stylesheets/vibey.css` and
   `docs/javascripts/channel.js` into the build (`properdocs.yml:14-17`). No config
   change is needed for this file to reach the built site; `exclude_docs`
   (`properdocs.yml:32-34`) only excludes `plans/**`, which does not match it.
2. Prove `sitemap.xml` is real, with a genuine build (not an assumption): `pip install
   'properdocs==1.6.7' 'properdocs-theme-mkdocs==1.6.7' && properdocs build --strict
   --site-dir <a throwaway directory>`, then check that directory contains both
   `sitemap.xml` and `robots.txt`, and that `sitemap.xml` is well-formed XML containing
   at least one `<loc>https://the-vibey-project.github.io/vibey/...</loc>` entry.
3. New `tests/meta/test_docs_site_seo_files.py`: one test reads `docs/robots.txt`
   directly off disk and asserts its `Sitemap:` line's URL host+path matches
   `properdocs.yml`'s own `site_url` plus `sitemap.xml` — so if `site_url` ever changes,
   this test catches a `robots.txt` that was not updated to match, rather than the two
   silently drifting apart (12.c again: one declared value, `site_url`, must not have a
   second, independently-typed copy inside `robots.txt`).

## Where to change
- Create `docs/robots.txt`.
- Create `tests/meta/test_docs_site_seo_files.py`. Copy the provenance header from
  `tests/meta/test_adr_counts.py:1`.

## Acceptance criteria
- [ ] `docs/robots.txt` exists, starts with `User-agent: *`, and its last non-blank line
      is `Sitemap: <properdocs.yml's site_url, with no double slash>sitemap.xml`.
- [ ] A real `properdocs build --strict` into a throwaway `--site-dir` produces both
      `sitemap.xml` and `robots.txt` at that directory's root.
- [ ] The built `sitemap.xml` parses as XML and contains at least one `<loc>` element
      whose text starts with `properdocs.yml`'s `site_url`.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_docs_site_seo_files.py` passes.
- [ ] `git diff --stat` touches exactly `docs/robots.txt` and
      `tests/meta/test_docs_site_seo_files.py`.

## Tests to write first (TDD)
`tests/meta/test_docs_site_seo_files.py`:
- `test_robots_txt_declares_allow_all`: `docs/robots.txt` contains `User-agent: *` and `Allow: /`.
- `test_robots_txt_sitemap_line_matches_site_url`: parse `properdocs.yml`'s `site_url`
  with `yaml.safe_load`; assert `docs/robots.txt`'s `Sitemap:` line equals
  `f"Sitemap: {site_url.rstrip('/')}/sitemap.xml"`.
- `test_built_site_emits_sitemap_and_robots` (marked so it can be skipped where network/
  pip install is unavailable, mirroring how `tests/meta/test_paper_renders.py` or
  similar build-dependent tests in this repository already handle an optional heavy
  dependency — check that file first and follow its skip convention rather than
  inventing a new one): installs `properdocs`/`properdocs-theme-mkdocs` into a
  throwaway venv or the current environment, builds into `tmp_path`, and asserts both
  files exist with the sitemap containing a real `<loc>`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta/test_docs_site_seo_files.py
    pip install 'properdocs==1.6.7' 'properdocs-theme-mkdocs==1.6.7' && properdocs build --strict --site-dir /tmp/vibey-seo-check && test -f /tmp/vibey-seo-check/sitemap.xml && test -f /tmp/vibey-seo-check/robots.txt

## Out of scope
- Wiring a permanent CI job that builds the root docs site on every PR — today only
  `release-surfaces.yml` builds it, at release time; a separate, larger change.
- The favicon, social-preview image, and OG/JSON-LD injection (`seo-favicon-social-image`,
  `seo-docs-structured-data`) — this lane does not touch `properdocs.yml`'s `theme:` key
  or any HTML post-processing, so it cannot collide with either.
- `llms.txt` (`seo-llms-txt`) — a different static passthrough file, specified in its own lane.
- README.md, pyproject.toml, ADRs, CHANGELOG.md, and CLAUDE.md/AGENTS.md/GEMINI.md.

Commit as `feat(docs): declare robots.txt and verify sitemap.xml generation`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
