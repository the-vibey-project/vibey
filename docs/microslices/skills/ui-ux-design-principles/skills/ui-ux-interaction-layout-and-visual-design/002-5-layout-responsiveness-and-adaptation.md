---
id: skill-5-layout-responsiveness-and-adaptation-cfaf5d5ddd
purpose: 5 layout responsiveness and adaptation
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-interaction-layout-and-visual-design/SKILL.md
requires: ["skill-4-input-and-interaction-37a01a16df"]
links: ["skill-6-visual-design-142165b7ff"]
---

## §5. Layout, Responsiveness, and Adaptation

### 5.1 The layout primitives

- **Grid** — a shared coordinate system. 12-column is a convention, not a law; what matters
  is that everything aligns to *something*.
- **Spacing scale** — a geometric or 4/8-px-based scale (4, 8, 12, 16, 24, 32, 48, 64).
  **The value of a scale is that it removes decisions and makes proximity consistent**
  (§1.3 → `ui-ux-cognition-heuristics-and-navigation`). Arbitrary spacing is the visual signature of an unsystematized product.
- **Alignment** — the cheapest way to look designed. Left-align text; align edges of related
  elements; avoid center-aligning long text (ragged left edges slow reading).
- **Measure (line length)** — **45–75 characters** for body text; ~66 is the classic
  optimum. Beyond ~90 the eye loses the line return. This constraint alone dictates
  layout on wide screens: full-width text at 1600 px is unreadable, which is why you need
  a max-width or a multi-column structure.
- **White space is not empty** — it is the mechanism of grouping and hierarchy. "Reducing
  white space to fit more" reliably makes things harder to find, not denser with
  information.

### 5.2 Responsive vs. adaptive, and the modern toolkit

**Responsive** = one fluid layout that reflows continuously. **Adaptive** = discrete
layouts swapped at breakpoints. In 2026 the practical answer is layered:

| Tool | Job |
|---|---|
| **Media queries** | Page-level structure (sidebar vs. stacked) |
| **Container queries** | **Component-level** adaptation — a card responds to *its own* available space, not the viewport. **Baseline Widely Available since August 2025** (~93% support). This is the biggest shift in responsive layout since media queries. |
| **`clamp()` fluid type/space** | Smooth scaling instead of jumps at breakpoints |
| **Intrinsic layouts** (`grid-template-columns: repeat(auto-fit, minmax(…, 1fr))`, Flexbox wrap) | Breakpoint-free layouts that just work |
| `dvh`/`svh`/`lvh` | The mobile-100vh problem (`svh` is safer where mid-scroll reflow is unacceptable) |
| `prefers-reduced-motion`, `prefers-color-scheme`, `prefers-contrast` | Respecting user settings |

```css
/* Container query: the component adapts to its context, not the window */
.card-wrap { container-type: inline-size; }
@container (min-width: 400px) {
  .card { display: grid; grid-template-columns: 120px 1fr; gap: 1rem; }
}

/* Fluid type. ⚠️ The max must not exceed ~2.5× the min, and the formula MUST
   include a rem component — a pure-vw font size fails WCAG SC 1.4.4 (Resize Text)
   because it doesn't respond to browser zoom. */
:root {
  --step-0: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --step-3: clamp(1.75rem, 1.4rem + 1.75vw, 3rem);
}
```

**[DURABLE] Breakpoints come from your content, not from a device list.** Resize the
browser slowly and put a breakpoint where the layout *breaks* — where the measure gets too
long, the columns get too narrow, the nav wraps. A breakpoint at 768 "because iPad" is a
coincidence, and the device it named has been irrelevant for years.

Useful *starting* ranges (then adjust to content): ~360–480 (phone portrait), ~481–767
(phone landscape / small), ~768–1023 (tablet), ~1024–1279 (small laptop), 1280+ (desktop).
Note the 768–1024 band is genuinely awkward: a single text column at 840 px exceeds the
optimal measure, but a phone layout wastes the space. Two-column, or one column with
generous side padding, is usually right.

### 5.3 Tablet — the form factor everyone under-designs

**[DURABLE] A tablet is not a big phone and not a small laptop.** The common failure is
shipping a stretched phone layout: a 1024 px-wide single column of full-width list rows
with a 900 px measure. The tablet-specific moves:
- **Split view / master–detail** is the defining tablet pattern. Use it.
- Support **multitasking**: Split View / Slide Over / Stage Manager on iPadAOS, and
  freeform/split windows on Android — meaning **your app can be any width at any time**,
  and orientation can change mid-session. This is where container queries and true
  size-class-driven layout pay off, and where "we only tested full-screen portrait" breaks.
- **Keyboard and trackpad/stylus attach and detach.** Support hover, shortcuts, and
  pointer precision when present, without requiring them.

### 5.4 Foldables and novel form factors

Foldables introduce: square-ish aspect ratios, ultra-wide unfolded states, a **hinge/fold
that content must not straddle**, and **continuity** — an app that must survive a fold/unfold
transition mid-task without losing state. Practical guidance: use adaptive layout driven by
available size (not device identity), handle configuration changes without recreating state,
avoid placing interactive elements across the fold, and test the fold transition explicitly.
Container queries handle much of this without device detection.

### 5.5 Density and platform expectations

Provide density *options* in data-heavy desktop and web apps (comfortable / compact). Users
of professional tools genuinely want more rows per screen; consumer users don't. This is
one of the few places where a preference toggle beats a designer's judgment.

---
