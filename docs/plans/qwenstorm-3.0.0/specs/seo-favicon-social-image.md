## Title
feat(docs): a declared favicon and Open Graph social-preview image for the docs site

## Why
There is not a single image asset anywhere in the repository
(`find . \( -iname '*.png' -o -iname '*.svg' -o -iname '*.ico' -o -iname '*.jpg' \)`
is empty). `properdocs.yml`'s `theme: mkdocs` line has no `favicon:` key, so every page
of the published site ships the base theme's own generic default tab icon, and there is
no image for `seo-docs-structured-data`'s `og:image`/`twitter:image` tags to point at —
which means every link to the docs site that gets shared in Slack, Discord, or on
social media currently unfurls with no preview image at all.

GitHub's own per-repository social-preview image (Settings → General → Social preview)
has no REST or GraphQL endpoint at all — it is upload-only, through the web UI. That one
surface genuinely cannot be declared as code, and this lane does not attempt it; it is
recorded here as a 10.f evidence-bounded exception, not silently skipped without a
reason on record. What this lane *can* do as code is the docs site's own favicon and the
image its pages advertise to link unfurlers.

## Required behaviour
1. Create `docs/img/favicon.svg`, exactly:
   ```svg
   <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="vibey">
     <rect width="64" height="64" rx="14" fill="#1a1033"/>
     <circle cx="18" cy="32" r="7" fill="#6f42c1"/>
     <circle cx="32" cy="32" r="7" fill="#3d76a8"/>
     <circle cx="46" cy="32" r="7" fill="#0a7ea4"/>
   </svg>
   ```
   Three dots over a dark rounded square, tracing the same purple-to-blue span as the
   README's own existing paper badge (`#6f42c1`) and book badge (`#0a7ea4`)
   (`README.md:9-10`) — the mark reads as the same brand, not a new one, and three dots
   left-to-right is a legible motif at 16×16 for "a queue/pipeline."
2. Create `scripts/generate_social_preview.py` (module-level functions, matching
   `scripts/paper_evidence.py`'s shape), producing a 1200×630 truecolor PNG with three
   equal vertical bands in the same three colors, using only the standard library
   (`struct`, `zlib` — no Pillow or other imaging dependency, per ADR-0017's "use what
   the family already has before reaching for a third-party equivalent", and here even
   the family has nothing simpler than the standard library for a flat three-band image):
   ```python
   from __future__ import annotations

   import argparse
   import struct
   import zlib
   from pathlib import Path

   WIDTH, HEIGHT = 1200, 630
   BANDS = ((0x6F, 0x42, 0xC1), (0x3D, 0x76, 0xA8), (0x0A, 0x7E, 0xA4))
   OUTPUT = Path("docs/img/social-preview.png")

   def band_color(x: int) -> tuple[int, int, int]:
       third = WIDTH // len(BANDS)
       return BANDS[min(x // third, len(BANDS) - 1)]

   def _chunk(tag: bytes, data: bytes) -> bytes:
       return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

   def render() -> bytes:
       rows = bytearray()
       for _y in range(HEIGHT):
           rows.append(0)
           for x in range(WIDTH):
               rows += bytes(band_color(x))
       ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
       idat = zlib.compress(bytes(rows), 9)
       return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")

   def main(argv: list[str] | None = None) -> int:
       parser = argparse.ArgumentParser()
       parser.add_argument("--check", action="store_true")
       args = parser.parse_args(argv)
       png = render()
       if args.check:
           if not OUTPUT.exists() or OUTPUT.read_bytes() != png:
               print(f"{OUTPUT} is stale; run without --check to regenerate")
               return 1
           return 0
       OUTPUT.write_bytes(png)
       return 0

   if __name__ == "__main__":
       raise SystemExit(main())
   ```
   Run `python3 scripts/generate_social_preview.py` once and commit the resulting
   `docs/img/social-preview.png`.
3. Change `properdocs.yml`'s `theme:` line from the bare scalar `theme: mkdocs` to a
   mapping that adds the favicon without changing the theme itself:
   ```yaml
   theme:
     name: mkdocs
     favicon: img/favicon.svg
   ```
4. Verify against a real build, since `favicon:` support is a claim about a package
   (`properdocs-theme-mkdocs`) this checkout does not vendor: `pip install
   'properdocs==1.6.7' 'properdocs-theme-mkdocs==1.6.7' && properdocs build --strict`,
   then check the built `site/index.html` actually references the new favicon rather
   than a bundled default. If the build fails or the favicon is not honoured, STOP and
   report BLOCKED with the exact error — do not fall back to a different, unverified
   mechanism.

## Where to change
- Create `docs/img/favicon.svg` and `docs/img/social-preview.png` (via the script).
- Create `scripts/generate_social_preview.py`.
- Edit `properdocs.yml`'s `theme:` key.

## Acceptance criteria
- [ ] `docs/img/favicon.svg` exists and is well-formed XML (`xml.etree.ElementTree.fromstring` parses it without error).
- [ ] `docs/img/social-preview.png` exists, is exactly 1200×630 (verified by reading the PNG's own `IHDR` chunk, not by trusting the generator), and `python3 scripts/generate_social_preview.py --check` exits 0 against it.
- [ ] `properdocs.yml`'s `theme:` is a mapping with `name: mkdocs` and `favicon: img/favicon.svg`.
- [ ] A real `properdocs build --strict` succeeds and the built homepage's `<head>` contains a `<link rel="shortcut icon" href=".../img/favicon.svg">`-shaped tag (exact attribute name may vary by theme version — assert the `href` value, not the `rel` value, if `--strict` output differs).
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_social_preview_image.py` passes.

## Tests to write first (TDD)
Create `tests/meta/test_social_preview_image.py` (provenance header copied from
`tests/meta/test_adr_counts.py:1`):
- `test_png_dimensions_are_1200_by_630`: parse the committed PNG's `IHDR` chunk directly
  with `struct.unpack`, independent of the generator module, so a bug in the generator
  that also miscounts its own output cannot pass silently.
- `test_png_matches_the_generator_exactly`: `generate_social_preview.main(["--check"])` returns 0.
- `test_favicon_svg_is_well_formed`: `ElementTree.fromstring` on the committed file.
- `test_properdocs_yml_theme_names_the_favicon`: parse `properdocs.yml` with
  `yaml.safe_load`; assert `theme["favicon"] == "img/favicon.svg"` and
  `theme["name"] == "mkdocs"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    python3 scripts/generate_social_preview.py --check
    uv run pytest -q -p no:cacheprovider tests/meta/test_social_preview_image.py
    pip install 'properdocs==1.6.7' 'properdocs-theme-mkdocs==1.6.7' && properdocs build --strict

## Out of scope
- The GitHub repository-level social-preview image — no API exists to set it; see Why.
- The OG/Twitter meta tags themselves that reference this image — `seo-docs-structured-data`.
- Any raster format beyond this one flat three-band PNG; a hand-drawn illustrated mark is
  a design decision for a human, not a mechanical spec.
- `robots.txt`/`sitemap.xml` (`seo-robots-sitemap`) and every other file in this wave.

Commit as `feat(docs): add a declared favicon and social-preview image`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
