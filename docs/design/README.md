<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# The design system

Every colour, face, size, space, radius, shadow, curve and sound cue that a vibey surface
uses comes from one place: `design/tokens/`. The docs sites, the paper, the VS Code
extension and every Krypton app read generated forms of those tokens and add no colour of
their own. The decision is [ADR-0062](../architecture/decisions/0062-one-design-system-for-every-surface.md).

## Two names, one atom

- **vibey** is the project, the engine and its documentation. Its wordmark is `vibey` in a
  monoline stroke, with the atom as the dot on the i.
- **Krypton** is every app and UI: the desktop app, the mobile and web app, and the editor.
  Its wordmark is `Krypton`, with the atom inside the o, and the app icons are Krypton's.

## The tokens

The files are in the DTCG format (the Design Tokens Community Group specification 2025.10):
each token has a `$value` and a `$type`, and a value written `{color.violet.425}` refers to
another token.

| File | What it holds |
|---|---|
| `color.primitive.tokens.json` | Tier 1, the palette: night, slate, violet, blue, cyan, teal, mint, green, gold, orange, red, magenta |
| `color.dark.tokens.json`, `color.light.tokens.json` | Tier 2, semantic roles, the same names in both themes |
| `color.print.tokens.json` | The paper's 17 TikZ colours, `vibeyink` to `vibeymist`, unchanged |
| `type.tokens.json` | Font families, weights, sizes, line heights and the named text styles |
| `space.tokens.json` | Spacing on a 4 px grid, corner radii, border widths |
| `elevation.tokens.json` | Shadows, 0 to 4 |
| `motion.tokens.json` | Durations, easings, transitions, and their reduced-motion twins ([Motion](motion.md)) |
| `sound.tokens.json` | Sound events and their length budgets; the audio arrives in `design/sounds/` |

**Components use tier-2 roles only**, never a primitive and never a raw hex. The roles are:

- **Surfaces:** `bg.canvas`, `bg.surface`, `bg.raised`, `bg.overlay`, `bg.code`.
- **Borders and focus:** `border.subtle`, `border.strong`, `focus.ring`.
- **Text:** `text.primary`, `text.secondary`, `text.tertiary`, `text.link`, `text.link-hover`,
  `text.on-accent`.
- **Accent:** `accent.default`, `accent.hover`, `accent.subtle`.
- **Status:** `status.success`, `status.warning`, `status.danger`, `status.info` and
  `status.ultra`. ULTRA is magenta, distinct from every other status.
- **Lanes and jobs:** `state.queued`, `state.running`, `state.awaiting-human`, `state.parked`,
  `state.succeeded`, `state.failed`, `state.cancelled`, `state.ultra`.
- **Charts:** `lane.1` to `lane.8`.
- **Code and decoration:** `syntax.*` for code, and `effect.*` for glass, glow and grid
  washes. Effects are decoration only, never text.

## Contrast is declared, and proven

`design/contrast.json` lists every foreground/background pair a surface may draw and the
WCAG 2.2 minimum it must meet: 4.5:1 for text, 3:1 for controls and chart marks. All 182
pairs pass in both themes. To see each ratio:

```bash
python3 scripts/design/generate.py --contrast
```

Code blocks on the docs site stay dark in both themes, by design.

## Three theme modes

Every GUI offers **Light**, **Dark** and **System**. System is the default: it follows the
operating system and switches live, and a choice persists per device.

| Surface | How it switches |
|---|---|
| CSS (docs, webviews) | `prefers-color-scheme` by default; `data-theme="light"` or `"dark"` on the root element overrides it |
| TypeScript | `ThemeMode = "light" \| "dark" \| "system"`, `resolveTheme()`, `coloursFor()` |
| GTK 4 / libadwaita | `AdwStyleManager`: system is `ADW_COLOR_SCHEME_DEFAULT`, light `FORCE_LIGHT`, dark `FORCE_DARK` |
| C | `VibeyThemeMode`, default `VIBEY_THEME_MODE_SYSTEM` |

The docs site has a three-way switch in its navigation bar.

## Type

Inter for every screen, JetBrains Mono (falling back to the platform monospace) for code and
lanes, and TeX Gyre Termes, Heros and Cursor for print. The named styles are display,
headline, title, subtitle, body, label, caption, overline and code.

## The mark: a krypton atom

The mark is krypton's most abundant isotope, Kr-84, with nothing else beside it:

- a nucleus of **36 protons and 48 neutrons**, packed as small lit spheres in two token
  colours, with the protons spread evenly among the neutrons;
- **four concentric shells** carrying the Bohr counts **2, 8, 18 and 8** electrons, each
  electron smaller than a nucleon;
- shell radii that grow as n² (1 : 4 : 9 : 16), **relaxed** so that the 84-nucleon cluster
  fits inside the first shell;
- each shell's electrons turned so the whole is balanced.

In animated contexts (web, apps, the splash screen) the shells turn gently at different
speeds, the outer ones slower, and under reduced motion every electron rests where the
static mark draws it.

**A hundred and twenty particles cannot be drawn at 16 px,** so the mark has levels of
detail, and the spacing is relaxed toward even as it shrinks:

| Level | Used at | Nucleus | Shells and electrons |
|---|---|---|---|
| full | 128 px and up | all 84 nucleons | four shells, 2/8/18/8 |
| medium | 48 to 64 px | a dozen nucleons | four shells, 2/4/6/4 |
| small | 22 to 32 px, the dot on the i, the o of Krypton | a blob with five nucleons | four shells, one or two electrons each |
| tiny | 16 px | a blob with three nucleons | **two** shells: four circles a pixel apart alias into a moiré |

## Generated outputs

One command writes everything, each file behind a "generated, do not edit" header:

```bash
python3 scripts/design/generate.py            # text outputs and SVG masters
python3 scripts/design/generate.py --rasters  # ...and every PNG, in about a minute
```

| Output | For |
|---|---|
| `design/dist/css/tokens.css` | Any web surface: custom properties and the three theme modes |
| `docs/stylesheets/vibey.css` and every docs site's copy, with `channel.js` | The documentation sites, from `design/web/`; the targets are in `design/design.json` |
| `design/dist/ts/tokens.ts` | `@vibey/core`, the React Native app, webviews |
| `design/dist/gtk/vibey.css`, `vibey-dark.css` | The desktop app's libadwaita styles |
| `design/dist/c/vibey_tokens.h` | `libvibeydesktop` |
| `design/dist/tex/vibey-colours.tex`, `vibey_gh/paper_palette.py` | The research paper |
| `design/identity/*.svg` | Mark, atom, both wordmarks and lockups, in dark and light, with animated versions; the app-icon tiers; Android adaptive layers; the social image |
| `design/dist/icons/` | PNGs: freedesktop hicolor, a macOS `vibey.iconset` (`iconutil -c icns` makes the `.icns`), iOS 1024 opaque, Android, favicons, a 1200×630 social preview |
| `clients/vscode/media/vibey.svg` | The editor's activity-bar glyph, in the theme's own colour |

The PNGs are drawn by a signed-distance renderer written in the standard library, so no
imaging dependency is needed and the output is the same to the byte on every machine.

## Changing anything

1. Edit a token (or `design/web/*` for the docs stylesheet and script).
2. Run the generator, adding `--rasters` if the identity changed.
3. Commit the outputs with the change.

`tests/meta/test_design_tokens_generated.py` fails if any output differs from what the
tokens generate, and runs the contrast audit. A Figma mirror of the tokens is linked from
the ADR; the JSON stays the source of truth.
