---
id: skill-2-the-10-foot-ui-ba1b6789fc
purpose: 2 the 10 foot ui
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-platforms-and-10-foot-ui/SKILL.md
requires: ["skill-1-the-platform-landscape-775d8a4035"]
links: ["skill-3-focus-and-input-411efcd90c"]
---

## §2. The 10-Foot UI

### 2.1 Why TV design is genuinely different

**[DURABLE] The name is the specification: the viewer is ~10 feet (3 m) away.** Everything
follows from that plus the D-pad:

| Constraint | Consequence |
|---|---|
| Viewing distance ~10× a phone | Everything must be far larger relative to the screen |
| No pointer | Only focusable elements are reachable — nothing is "clickable" |
| No hover | Every affordance must be visible in the default state |
| No text input worth the name | On-screen keyboards are miserable; minimize typing (§3.4) |
| Shared/social viewing | Others are watching you navigate. Errors are public |
| Lean-back intent | The user wants to *watch*, not to *operate a UI* |
| Ambient light varies wildly | Contrast must survive a sunlit room and a dark one |
| Overscan on older sets | Content near the edge may be physically cut off |

### 2.2 The numbers

- **Design canvas: 1920×1080**, scaled to 4K by the platform. Most platforms want 1080p
  assets; a few accept 4K UI. **Design at 1080p and let the compositor scale.**
- **Safe area: keep all UI inside ~90% of the screen** — i.e. a **5% margin on every
  side** (≈96 px horizontally, ≈54 px vertically at 1080p). Older sets overscan; text at
  the edge disappears.
- **Minimum body text ~24 px at 1080p**; titles 32–48 px. **Anything under ~18 px is
  unreadable at 10 feet** regardless of what it looks like on your monitor.
- **Focusable targets ≥ 60–80 px** in their smallest dimension, with clear separation.
- **Contrast**: aim well above the WCAG 4.5:1 minimum. **Avoid pure white (#FFFFFF) on
  large areas** — on a bright HDR panel in a dark room it's genuinely painful; use ~#F0F0F0
  or lower. Similarly avoid pure black backgrounds on OLED for UI chrome that persists.
- **Avoid thin fonts and hairline strokes.** Compression, upscaling, and chroma subsampling
  destroy them.
- **Frame budget: 16.6 ms at 60 Hz** — and TV silicon will miss it far more easily than
  a phone (§6 → `smart-tv-playback-drm-and-performance`).

### 2.3 The standard layout vocabulary

**[DURABLE] TV UI has converged on a small set of patterns, and deviating from them costs
you.** Users navigate a dozen apps with the same muscle memory:
- **The rail/row grid** — horizontal shelves of posters, vertically stacked by category.
  This is *the* content-browse pattern on every platform.
- **Hero/spotlight** at the top with a featured item.
- **Left sidebar nav**, often collapsed to icons until focused.
- **Detail page** — big art, synopsis, a primary CTA (Play/Resume) that must be the first
  focused element.
- **Player with a transport overlay** that auto-hides.
- **Grid** for search results and full catalogues.

**⚠️ Do not invent a novel navigation model.** The cost is not aesthetic — a user who
can't find the back-out path with a D-pad simply leaves, and you will never learn why.

---
