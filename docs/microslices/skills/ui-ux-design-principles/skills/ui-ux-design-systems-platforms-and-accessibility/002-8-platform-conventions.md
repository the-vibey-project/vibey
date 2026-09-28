---
id: skill-8-platform-conventions-99ec8151b2
purpose: 8 platform conventions
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-design-systems-platforms-and-accessibility/SKILL.md
requires: ["skill-7-design-systems-and-tokens-87b471c0fb"]
links: ["skill-9-accessibility-e78062161b"]
---

## §8. Platform Conventions

**[DURABLE] Jakob's Law applies to platforms.** Users bring expectations from every other
app on that OS. Violating them is expensive; the only good reason is that the convention is
genuinely wrong for your domain, and you should be able to say why.

### 8.1 Apple — HIG, and Liquid Glass

Core Apple principles: **clarity, deference (content over chrome), depth**. Concretely:
- Navigation is hierarchical (push/pop), flat (tabs), or content-driven.
- **44 × 44 pt** touch targets; **Dynamic Type** support; SF Symbols for iconography.
- Back navigation is top-left plus edge-swipe; there is no system Back button.
- Modality is a strong statement — use sheets for focused sub-tasks, alerts sparingly.
- macOS additionally expects a full menu bar, multiple windows, unlimited undo (§8.4).

**macOS 26 / iOS 26 introduced Liquid Glass** — a translucent, light-refracting material
across toolbars, sidebars, tab bars, sheets, popovers, controls, the Dock and menu bar.
What matters for design work:
- **Framework chrome adopts it free on recompile** against the 26 SDK, across SwiftUI,
  UIKit and AppKit. **Custom components do not** — that's where the work is.
- Opt-in APIs: `.glassEffect()`, `GlassEffectContainer`, `glassEffectID` for morphing.
- Navigation now *floats over* content, which changes safe-area assumptions.
- Icons require rework via **Icon Composer** (layered vector, blur/translucency, specular
  highlights) — the flat 1024 px PNG workflow is obsolete.
- **⚠️ Accessibility:** translucency degrades text contrast. Respect **Reduce Transparency**
  and **Increase Contrast**, and test with both on. Apple's own first-year implementation
  drew substantial legibility criticism; treat restraint as the default.

### 8.2 Google — Material 3 and M3 Expressive

Material 3 brought dynamic color (Material You), a token-based architecture, and adaptive
layouts. **Material 3 Expressive** (announced May 2025) is an *enhancement to M3, not "M4"*,
adding a physics-based motion system, an expanded type scale with emphasized styles, a shape
system with morphing, and bolder color.

**It is unusually well-evidenced for a design language.** Google reports **46 research
studies with 18,000+ participants over ~3 years**, using eye-tracking, surveys and usability
trials. Reported findings: users spotted key UI elements **up to 4× faster** than in prior
Material 3; time-to-tap on key actions decreased significantly; and — the most interesting
result — **the usability age gap largely disappeared**, with older participants spotting key
elements as quickly as younger ones.

**[CONTESTED] How much to generalize from that.** The studies are Google's own, largely
unpublished in peer-reviewed venues, and measure Google's components in Google's contexts.
The mechanism behind the headline result is not mysterious — bigger, bolder, better-placed
primary actions are easier to find, which Fitts and von Restorff already predicted. The
honest reading: **the direction is well-supported (expressiveness and usability are not
opposed, and prominence helps older users disproportionately); the specific multipliers
should not be quoted as universal.** Google's own team notes the intent isn't to make every
interaction playful — "you might not want a super-playful UI for paying a parking ticket."

Android specifics that trip up iOS-first designers: the **system Back** (gesture or button)
with defined semantics, the **app bar** rather than a centered title, **FAB** for a single
primary action, **48 dp** targets, and Material's own navigation components (nav bar, nav
rail for tablets, nav drawer).

### 8.3 Web

The web has no HIG — it has conventions, and breaking them is more costly than on any
native platform because users arrive with expectations from the entire internet:
- Logo top-left links home. Nav in the header. Search where search goes.
- **Links look like links** (underline or unambiguous styling) and behave like links
  (middle-click, right-click, ⌘-click all work — which requires a real `<a href>`, not a
  `<div onClick>`).
- Browser **Back must work**, including in SPAs.
- Forms submit on Enter. Autofill works (correct `autocomplete` attributes — this is both
  a conversion and an accessibility feature).
- **Never disable zoom** (`user-scalable=no` / `maximum-scale=1`) — WCAG failure and a
  hostile act toward low-vision users.
- Respect `prefers-color-scheme`, `prefers-reduced-motion`, `prefers-contrast`.

### 8.4 Desktop (macOS / Windows / GNOME / KDE)

- **Menu bar as complete command index.** Every command should appear in a menu even if
  it's also a toolbar button — that's how Help search, keyboard discovery, and accessibility
  find it.
- **Unlimited, coalescing undo.** Typing 30 characters is one undo step.
- **Multi-window and window-state restoration** are baseline expectations, not features.
- **Keyboard-first** operation; show shortcuts in menus.
- **Density is higher and users want it.** Desktop is where power users live.
- **[PLATFORM] Linux is not one convention.** GNOME's HIG favours header bars with a
  hamburger and no menu bar; KDE retains traditional menu bars and far more configurability.
  Pick per your target desktop and be internally consistent; use libadwaita/KDE components
  and you inherit the right answer.

### 8.5 Cross-platform: consistency vs. nativeness

**[CONTESTED]** Brand-consistent-everywhere (Flutter, a strong web design system) versus
native-idiomatic-per-platform (SwiftUI + Material + platform toolkit).
- *For consistency*: one design, one implementation, one QA surface; users recognize your
  product across devices; cheaper by a large factor.
- *For nativeness*: users' expectations are set by the platform, not by you; native
  components carry accessibility, localization, dark mode, dynamic type, and platform
  updates **for free**; the uncanny-valley cost of "almost native" is real and is felt as
  low quality.
- **The defensible split:** be brand-consistent in *identity* (color, type, tone, iconography,
  illustration) and platform-native in *interaction* (navigation model, gestures, controls,
  system integration). Users forgive different-looking; they don't forgive different-behaving.

---
