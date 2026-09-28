---
id: skill-6-visual-design-142165b7ff
purpose: 6 visual design
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-interaction-layout-and-visual-design/SKILL.md
requires: ["skill-5-layout-responsiveness-and-adaptation-cfaf5d5ddd"]
links: []
---

## §6. Visual Design

### 6.1 Typography

**[DURABLE] Typography is 90% of most interfaces, and hierarchy is 90% of typography.**
- **Type scale**: a modular scale (ratios ~1.125 minor second → 1.5 perfect fifth). Fewer
  sizes is better; 5–7 steps covers nearly everything. Every extra size is a decision
  someone will make inconsistently.
- **Hierarchy comes from size + weight + color + space — not size alone.** A well-designed
  hierarchy can use two sizes and be perfectly clear.
- **Body text**: ≥16 px on web (smaller triggers mobile zoom and fails low-vision users);
  line-height ~1.4–1.6 for body, tighter (1.1–1.25) for large headings.
- **Measure**: 45–75 characters (§5.1).
- **Never disable user font scaling.** iOS Dynamic Type and Android font scale are used by
  a large number of people; a layout that breaks at 200% text is a WCAG 1.4.4 failure
  (Level AA) and an ordinary usability failure for anyone over 45.
- **All-caps** reduces reading speed for anything longer than a couple of words — fine for
  a label, wrong for a sentence. **Letter-spacing** should increase slightly for all-caps
  and small text, decrease for large display text.
- **System fonts** (SF Pro, Roboto, Segoe, Inter, the `system-ui` stack) load instantly,
  render optimally, and support the full glyph range. Custom fonts cost LCP; subset them,
  `preload` the critical weight, and use `font-display: swap` (or `optional`) — an unstyled
  or invisible text flash is a CLS and a perceived-performance problem.

### 6.2 Color

- **Build a semantic layer.** Never let a component reference `blue-500`; let it reference
  `color.action.primary`, which *resolves* to `blue-500` in light mode and `blue-300` in
  dark. Without this layer, dark mode and theming are a rewrite (§7.2 → `ui-ux-design-systems-platforms-and-accessibility`).
- **Perceptually uniform color spaces (OKLCH/LCH)** make generating consistent ramps far
  easier than HSL, where equal lightness values look wildly different across hues. The DTCG
  token spec now includes advanced color support for exactly this reason.
- **Never encode meaning in color alone** (WCAG 1.4.1). ~8% of men have some form of color
  vision deficiency. Pair color with icon, text, pattern, or position. "Red row = error" is
  a failure; "red row with an error icon and a message" is not.
- **Contrast (see §9.3 → `ui-ux-design-systems-platforms-and-accessibility` for the standards fight):** WCAG 2.2 requires **4.5:1** for body
  text, **3:1** for large text (≥18 pt / 14 pt bold) and for UI components and graphical
  objects (SC 1.4.11).
- **Dark mode is not inverted light mode.** Pure black backgrounds with pure white text
  cause halation for many readers (especially with astigmatism); use a very dark gray
  (~#121212) and slightly desaturated, lighter foreground colors. Elevation in dark mode is
  expressed by *lighter* surfaces, not by shadows (shadows are nearly invisible on dark).
  Desaturate saturated brand colors or they vibrate.

### 6.3 Space, elevation, and depth

- **Spacing scale** (§5.1) — 4 or 8 px base, geometric growth.
- **Elevation** communicates layering and modality: content < raised card < sticky header <
  dropdown < modal < toast. Keep the z-index scale as **named tokens**, not magic numbers
  (`z.modal: 1000`), or you will end up with `z-index: 99999`.
- Use **one** depth language. Mixing shadows, borders, and background-fills to mean the
  same thing produces visual noise.

### 6.4 Iconography

- **Icons are not universally understood.** Only a handful are (search 🔍, home, print,
  trash, back arrow, close ×, play). Everything else — especially abstract product concepts
  — needs a **text label**. Icon-only toolbars are consistently outperformed by icon+label
  in findability testing.
- Consistent grid, stroke weight, corner radius, and optical size across the set.
- **Tooltips are not a solution on touch** (no hover, §4.1).
- Every icon that conveys meaning needs an accessible name; every purely decorative icon
  needs to be hidden from assistive tech (`aria-hidden="true"`, `alt=""`).

### 6.5 Motion

**[DURABLE] Motion's job is to explain, not to decorate.** Legitimate uses:
1. **Continuity** — show where a thing came from and went (shared-element transitions).
2. **Feedback** — confirm the tap registered.
3. **Attention** — direct the eye to a change.
4. **Perceived performance** — mask latency, communicate progress.

Timing: **UI transitions 150–300 ms**; enter slightly slower than exit; larger objects
slower than small ones. Easing: **ease-out for entering** (fast then settle),
**ease-in for exiting**. Linear easing looks mechanical and is almost always wrong.
Spring/physics-based motion (now first-class in Material 3 Expressive and SwiftUI) feels
more natural for direct-manipulation gestures because it preserves velocity continuity.

**`prefers-reduced-motion` is not optional.** Vestibular disorders make large parallax,
zoom, and slide animations genuinely nauseating. Honour the setting by replacing motion
with a cross-fade or an instant change — not by removing the feedback entirely.

### 6.6 Perceived performance is a design material

| Wait | Design response |
|---|---|
| < 100 ms | Feels instant. Do nothing. |
| 100 ms – 1 s | Users notice but stay in flow. Subtle state change. |
| 1 – 10 s | **Show progress.** Skeleton screens > spinners (they signal structure). Determinate > indeterminate. |
| > 10 s | Progress + estimate + **cancel** + ability to leave and be notified. |

**Optimistic UI** (apply the change immediately, reconcile with the server later) is the
single most effective perceived-performance technique — and the most commonly botched.
The rule: if you show success optimistically, you owe the user an honest, non-destructive
recovery when it fails. Silently reverting is worse than having waited.

**Core Web Vitals** are the closest thing the web has to a shared performance contract, and
they are field metrics (real Chrome users, 75th percentile, 28-day window) — not lab scores:

| Metric | "Good" threshold | What it measures |
|---|---|---|
| **LCP** | ≤ **2.5 s** | Loading — when the largest visible element paints |
| **INP** | ≤ **200 ms** | Responsiveness — full interaction lifecycle (**replaced FID in March 2024**) |
| **CLS** | ≤ **0.1** | Visual stability — unexpected layout shift |

**INP is the one most sites fail** (roughly 43% miss the 200 ms threshold), because fixing
it requires JavaScript architecture changes — yielding to the main thread, breaking up long
tasks — not just compressing an image. **CLS is the most *design*-caused**: always set
explicit `width`/`height` (or `aspect-ratio`) on images, videos, iframes, and ad slots, and
reserve space for anything that loads late.
