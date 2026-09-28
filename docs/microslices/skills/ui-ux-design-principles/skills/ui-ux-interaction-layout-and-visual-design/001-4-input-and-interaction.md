---
id: skill-4-input-and-interaction-37a01a16df
purpose: 4 input and interaction
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-interaction-layout-and-visual-design/SKILL.md
requires: []
links: ["skill-5-layout-responsiveness-and-adaptation-cfaf5d5ddd"]
---

## §4. Input and Interaction

### 4.1 The input models are genuinely different

| | Touch | Mouse/trackpad | Keyboard | Voice | Stylus |
|---|---|---|---|---|---|
| Precision | Low (~9 mm) | High (1 px) | N/A (discrete) | N/A | Very high |
| Hover state | **None** | Yes | Focus | No | Hover on some |
| Right-click / secondary | Long-press | Yes | Context key | No | Barrel button |
| Multi-select | Awkward; needs a mode | Shift/Ctrl-click, marquee | Shift+arrows | No | Lasso |
| Precision editing | Painful | Good | Excellent | Poor | Excellent |
| Occlusion | **Hand covers content** | None | None | None | Hand covers |
| Discoverability | Poor (gestures invisible) | Medium | Poor without hints | Very poor | Poor |

**[DURABLE] The absence of hover on touch is a structural problem, not a detail.** Every
tooltip, every "reveal on hover" action, every hover-based preview has no touch equivalent.
Designing hover-dependent affordances means designing a desktop-only feature. And on hybrid
devices (touchscreen laptops, iPad + trackpad), *both* are possible simultaneously — so
design for the capability, not the device class (`@media (hover: hover)` and
`(pointer: coarse|fine)` exist for exactly this).

### 4.2 Touch targets — the numbers

| Standard | Minimum | Nature |
|---|---|---|
| **WCAG 2.2 SC 2.5.8 (AA)** | **24 × 24 CSS px** — or smaller with ≥24 px spacing | Legal floor for web |
| **WCAG 2.2 SC 2.5.5 (AAA)** | 44 × 44 CSS px | Aspirational |
| **Apple HIG** | **44 × 44 pt** | Platform convention (iOS/iPadOS); visionOS recommends ~60 pt because gaze+pinch is less precise |
| **Material Design** | **48 × 48 dp** (~9 mm physical) | Platform convention |
| Automotive (Google Design for Driving) | ~76 dp | Context raises the bar |

**Practical rule: design to 44–48 px minimum for anything touchable; treat WCAG's 24 px as
a floor you never actually approach.** The visual element can be smaller than the hit
target — pad it. `min-height: 44px` with the icon at 24 px inside is the standard fix.

Spacing matters as much as size: adjacent targets need ≥8 px of gap; destructive actions
need ≥16 px of separation from anything else.

### 4.3 Reach and the thumb zone

**[DURABLE, with caveats]** One-handed phone use concentrates comfortable reach in the
lower-center of the screen; top corners (especially the *opposite* top corner from the
holding hand) are hardest. Consequences:
- Primary actions belong at the **bottom** on mobile. This is why bottom sheets, bottom
  tab bars, and bottom-anchored primary buttons became standard — and why iOS moved the
  Safari address bar down.
- Destructive or rarely-used actions can live up top.
- **⚠️ Caveat:** the "thumb zone" heat maps that circulate are illustrative, not
  measured law; grip varies (one-handed 49%, cradled 36%, two-handed 15% in the
  often-cited Hoober observational study), and screens have grown since. Use it as a
  prior, not a proof.

### 4.4 Gestures

**[DURABLE] Gestures are invisible, unlabeled, and unmemorable.** Every gesture needs:
1. A **visible alternative** (a button that does the same thing), *always*.
2. A **discovery mechanism** (a hint animation on first use, a partially-revealed
   affordance like a peeking drawer edge, or an onboarding coach mark used sparingly).
3. **Reversibility** — swipe-to-delete without undo is a design defect.

Reserve system gestures: edge swipes (back/home/control center), pull-to-refresh at scroll
top, pinch-zoom. Overloading these produces conflicts users experience as "the app is
broken."

### 4.5 Keyboard — the accessibility and the power-user story at once

**[DURABLE] Full keyboard operability is simultaneously an accessibility requirement
(WCAG 2.1.1, Level A) and the single biggest efficiency win for expert users.** They are
the same feature.
- **Logical tab order** matching visual order. `tabindex` above 0 is almost always a bug.
- **Visible focus indicator** — WCAG 2.2 added SC 2.4.11 *Focus Not Obscured* and SC 2.4.13
  *Focus Appearance*. Removing `:focus` outlines without a replacement is a Level A failure.
  Use `:focus-visible` to satisfy both the mouse aesthetes and the keyboard users.
- **Escape closes; Enter confirms.** Universally expected.
- **No keyboard traps** (WCAG 2.1.2). Modals must trap *deliberately* and release on close.
- **Skip links** on the web so keyboard users can bypass repeated nav.
- Shortcuts: match platform conventions (⌘ vs Ctrl), show them in menus and tooltips, and
  don't override browser/OS reserved combinations.

### 4.6 Feedback and state

Every interactive element needs a designed **default, hover, focus, active, disabled,
loading, error, and selected** state. Missing states are where interfaces feel cheap.

**On disabled buttons [CONTESTED]:** the classic guidance is to disable a submit button
until the form is valid. The counter-position — now the majority view among accessibility
practitioners — is that disabled buttons are invisible to some assistive tech, give no
explanation, and leave the user stuck with no feedback about *why*. **Preferred pattern:
keep the button enabled, and on click, validate, focus the first error, and announce it.**
Reserve `disabled` for states that are genuinely unavailable for reasons the user already
understands.

---
