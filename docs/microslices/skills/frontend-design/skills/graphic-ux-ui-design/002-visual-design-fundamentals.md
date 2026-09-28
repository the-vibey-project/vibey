---
id: skill-visual-design-fundamentals-d7d4e76546
purpose: visual design fundamentals
source: src/vibey_tools/skills/plugins/frontend-design/skills/graphic-ux-ui-design/SKILL.md
requires: ["skill-evidence-summary-cb007730a9"]
links: ["skill-component-and-interaction-patterns-8ecf9a6773"]
---

## Visual Design Fundamentals

### Color Systems

Production color architecture uses three token tiers:
- **Primitive tokens**: raw values — `blue-500: #3B82F6`
- **Semantic tokens**: intent — `color-action-primary`, `color-text-primary`, `color-status-error`
- **Component tokens**: scoped — `button-bg-primary`

Applications consume semantic tokens, not primitives. Theming and dark mode become a matter of re-pointing semantic tokens, not editing components. Neutral scales (9–12 steps) carry most of the surface area.

### WCAG Contrast Requirements

| Level | Normal text | Large text (≥24px or 18.7px bold) | Non-text UI |
|-------|-------------|-----------------------------------|-------------|
| AA    | 4.5:1       | 3:1                               | 3:1         |
| AAA   | 7:1         | 4.5:1                             | —           |

Global regulations (Section 508, EN 301 549, AODA) target AA. AAA is aspirational and not always achievable. Low-contrast text is the #1 accessibility defect for seven straight years. **Do not wait for WCAG 3/APCA to be final** — keep conforming to WCAG 2.x AA for compliance; use APCA as a supplementary check (especially for dark themes); never claim "WCAG 3 compliance" (it doesn't exist yet as of 2026).

### Oklch and Wide-Gamut Color

CSS Color Level 4 (`oklch()`, `oklab()`, `color(display-p3)`) is Baseline Widely Available (Chrome/Edge 111+, Firefox 113+, Safari 15.4+).

Why oklch matters:
1. **Perceptual uniformity** — a fixed change in L looks equally different across hues; HSL does not have this property. Use it to generate consistent tint/shade scales programmatically.
2. **Wide gamut** — Display P3 covers ~50% more colors than sRGB. Every iPhone since 7, every MacBook since 2016 supports it.

Always declare sRGB hex fallbacks first for old browsers.

### Dark Mode

**Never use pure black (#000000).** Material Design recommends #121212 as the base dark surface — pure black causes halation/blooming and disables shadows.

Express elevation through lightness, not shadow:

| Layer       | Approximate L% |
|-------------|----------------|
| Base        | 10–12%         |
| Sidebars    | 14–16%         |
| Cards       | 17–20%         |
| Modals      | 22–26%         |
| Popovers    | 26–30%         |

Keep ~3–5 points between each level. Desaturate accent colors (they vibrate against dark surfaces). Use off-white (~#E1E1E1 or white at 87% opacity) rather than pure white text. A naive light-palette inversion fails — light and dark modes have asymmetric perceptual requirements. Always let users toggle; don't force it.

### Typography

| Guideline             | Value                     |
|-----------------------|---------------------------|
| Optimal line length   | 50–75 characters (66ch sweet spot) |
| WCAG line length cap  | 80 characters (40 for CJK) |
| CSS implementation    | `max-width: 66ch`         |
| Line height (body)    | ~1.5                      |
| Fluid type            | `clamp()` to preserve ch range across viewports |

Hierarchy priority: size → weight → color → spacing. Adding typefaces is the classic mistake. Variable fonts are worth the complexity only when shipping multiple weights/widths.

**Web font loading**: `font-display: swap` (or `optional` for CLS-sensitive cases), `<link rel="preload">` for the critical font, `size-adjust`/`ascent-override` on fallback `@font-face` to minimize layout shift.

### Layout and Grid

- **8pt grid** with a 4pt sub-grid is the de facto spacing system
- **12-column grids** dominate web layout
- Use **CSS Grid** for two-dimensional layout; **Flexbox** for one-dimensional component distribution
- The F-pattern (NN/g, 2006, confirmed 2017) is a symptom of poor formatting, not a goal. Good headings, bolding, and front-loaded content replace F-scanning with more thorough "layer-cake" scanning
- Users read at most 28% of words on a page on average (Nielsen, 2008, ~50,000 page views); 20% is more likely
- Gestalt principles (proximity, similarity, continuity, closure, figure-ground) are the most practically useful perceptual framework

**Content density is a genuine fork:**
- Dense UIs: correct for pro tools, dashboards, IDEs, analytics (information-per-screen, expert efficiency)
- Airy UIs: correct for consumer onboarding and marketing (reduce cognitive load, guide one action)

---
