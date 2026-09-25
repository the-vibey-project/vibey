# 0065 — One design system for every surface

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrines 12.k (the Beauty Law, proposed), 12.c, 12.e, 10.f, 9.b; the Beauty Bar (`docs/design/beauty-bar.md`) · **Related:** ADR-0062, ADR-0016, ADR-0017, ADR-0018, ADR-0023, ADR-0059 · **Evidence:** `develop` at `0a2f856e`, read 2026-09-25

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`, all done in the change that
carries it.

## Context

The operator made beauty law on 2026-09-25 ("insanely beautiful ... and fun"), and the
client suite (desktop in C/GTK, React Native mobile and web, the VS Code extension) is a
3.0.0 release gate. None of those surfaces can share a look without shared decisions, and
there were none:

- The docs site's dark palette lived in `vibey.css`, and that file existed in **three
  drifted variants** across ten locations (the root site, vibey-gh's packaged and installed
  copies, and six tenant sites). Each variant was a strict superset of the last; fixes had
  landed in one and not the others. `channel.js` had drifted the same way.
- The research paper had its own 17-colour light palette, typed into `paper.py`.
- The extension used VS Code's variables, and nothing else had any tokens at all.
- There was no light theme for the site, no logo beyond a 24-px outline glyph, and no icon,
  favicon or social image (`seo-favicon-social-image.md` was unimplemented).

## Decision

**`design/tokens/*.tokens.json`, in the DTCG format (the Design Tokens Community Group
specification 2025.10), is the single source of every colour, face, size, space, radius,
shadow, curve and sound cue a vibey surface uses.** Three tiers: a primitive palette
(tier 1); semantic roles per theme (tier 2: `bg.*`, `text.*`, `accent.*`, `status.*`
including a distinct magenta **ULTRA**, `state.*` for lanes and jobs, `lane.1..8` for
charts, `syntax.*`, `effect.*`); and the paper's print palette as aliases. Surfaces use
tier-2 roles only.

1. **One family, two deliberate themes.** The site's night palette is the dark theme; the
   paper's ink-on-white palette is the light theme. The hues are shared (violet, cyan/blue,
   mint), so the two read as one brand. The paper's 17 colours keep their names, order and
   values: its rendering is unchanged in meaning, and a test pins it.
2. **Three theme modes everywhere: Light, Dark, System** (operator, 2026-09-25). System is the
   default, follows the OS and switches live; the choice persists per device. CSS follows
   `prefers-color-scheme` unless `data-theme` on the root says otherwise; TypeScript exports
   `ThemeMode` and `resolveTheme`; GTK maps the mode onto AdwStyleManager's colour scheme
   (the C header carries the enum). The docs site gains a three-way switch.
3. **Contrast is declared and proven.** `design/contrast.json` lists every
   foreground/background pair a surface may draw and its WCAG 2.2 minimum; 182 pairs pass in
   both themes, and the audit runs in `tests/meta/test_design_tokens_generated.py`. Code
   blocks stay dark in both themes, by design, and keep vibey-gh's own contrast tests green.
4. **Generators, not copies.** `scripts/design/` (classes behind
   `scripts/interfaces/design_interface.py`, ADR-0016) emits the CSS token layer, the one docs
   stylesheet and `channel.js` to every target listed in `design/design.json`, a TypeScript
   module for `@vibey/core`/React Native/webviews (`design/dist/ts/tokens.ts`), GTK CSS and a C
   header for the desktop app, a TeX palette, and `vibey_gh/paper_palette.py`, which the paper's
   preamble splices in. The gh tenant installs on its own, so its palette is generated *into*
   the package rather than read from `design/` at runtime. Every output carries a
   "generated, do not edit" header, and the meta test fails on drift (12.e).
5. **Identity from the same tokens: the mark is a krypton atom** (operator, 2026-09-25).
   The extension's V glyph was the starting point; the operator replaced it with the atom
   alone. krypton (Z = 36) has exactly four electron shells; the mark is its most abundant
   isotope, Kr-84: a nucleus of 36 protons and 48 neutrons packed as small lit spheres in two
   token colours (protons interleaved evenly among neutrons on a sunflower spiral), and four
   concentric circular shells carrying the Bohr counts 2, 8, 18 and 8. Radii grow as n²
   (`r = 0.253 + 0.0467 n²` of the outer radius), relaxed from the pure 1 : 4 : 9 : 16 so the
   84-nucleon cluster fits inside the first shell; electrons are smaller than a nucleon. Each
   shell's electrons are turned so the whole is balanced (the pair vertical, the octets
   interleaved). In animated contexts the shells turn at different speeds, outer ones slower,
   derived from `motion.duration.ambient`, and rest where they are drawn under reduced motion.
   The same atom is the dot on the i of the monoline wordmark.

   **Levels of detail, because 120 particles cannot be drawn at 16 px:** `full` (every nucleon
   and electron) from 128 px; `medium` (12 nucleons, 2/4/6/4 electrons) at 48–64 px; `small`
   (a nucleus blob with five nucleons, four evenly spaced shells, one or two electrons each) at
   22–32 px and on the i; `tiny` at 16 px keeps **two** shells, because four circles a pixel
   apart alias into a moiré there (checked by rendering, not assumed). Spacing is relaxed
   toward even at the smaller levels for legibility.

   SVG masters (mark, atom, wordmark, lockup, each in dark and light palettes, plus animated
   versions, the app-icon tiers, Android adaptive layers and a 1200×630 social image) live in
   `design/identity/`. PNGs (freedesktop hicolor, a macOS `.iconset` for `iconutil`, iOS 1024
   opaque, Android, favicons, social) are drawn by a **standard-library signed-distance
   renderer** in `scripts/design/identity.py`.

## Alternatives considered

- **Style Dictionary.** The reference DTCG toolchain, but it brings Node into a Python
  build that needs nothing else from it; the resolver here is ~100 lines of stdlib. If a
  future client needs a transform this lacks, adding Style Dictionary is the move, recorded
  then.
- **cairosvg or Pillow for rasters.** cairosvg needs the system cairo library, Pillow cannot
  draw SVG, and neither is in the dev extras. No dependency was added: the SDF renderer is
  exact for the shapes the mark uses, deterministic to the byte, and lets the drift test
  re-draw icons with nothing installed. The raster set takes about 16 s, so `--check`
  re-draws the two smallest and verifies the rest by the manifest's scene hashes.
- **Symlinks instead of generated copies.** vibey-gh's wheel force-includes its copy and
  `vibey-gh install` installs another into adopters' repositories; symlinks survive neither.
- **Light theme only for the site.** Rejected by the operator's three-mode rule.

## Consequences

- **Figma mirror:** [vibey design system](https://www.figma.com/design/qQRaiLoOrh6NsYQHS5LVmx)
  holds the tokens as variables (66 palette, 72 semantic roles in each theme, 23 space and
  radius). The operator's Figma plan allows one mode per collection, so Light and Dark are two
  collections (`vibey / theme / Light`, `vibey / theme / Dark`) rather than two modes of one.
  The JSON remains the source of truth; the Figma file is a mirror, refreshed from it.

- The ten docs stylesheets and `channel.js` copies are now one generated file each; editing
  one by hand fails the meta test. The source is `design/web/`.
- Every client lane (F, G, H, I, J) consumes `design/dist/` and adds no colour of its own.
- **Left open:** the sound files (Lane J, `design/sounds/`); the `.icns` binary itself
  (`iconutil -c icns design/dist/icons/macos/vibey.iconset` on macOS, at packaging time); and
  wiring the favicon and social image into
  `properdocs.yml`'s theme and meta tags (`seo-docs-structured-data`).
