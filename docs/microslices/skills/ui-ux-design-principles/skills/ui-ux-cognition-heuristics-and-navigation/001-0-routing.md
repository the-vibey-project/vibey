---
id: skill-0-routing-efd17c5aba
purpose: 0 routing
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-cognition-heuristics-and-navigation/SKILL.md
requires: []
links: ["skill-1-the-science-underneath-why-interfaces-work-or-don-t-bfea79d860"]
---

## §0. Routing

### 0.1 The four form factors, honestly compared

| | **Mobile** | **Tablet** | **Web (desktop browser)** | **Desktop (native)** |
|---|---|---|---|---|
| Primary input | Thumb, one hand, imprecise | Two hands / stylus | Mouse + keyboard | Mouse + keyboard, heavy shortcut use |
| Pointer precision | ~9 mm finger contact | ~9 mm, better reach | ~1 px | ~1 px |
| Session length | Seconds–minutes | Minutes | Minutes | Hours |
| Attention | Divided, interrupted, mobile | Semi-focused, leisure | Task-focused, multi-tab | Deep focus, expert |
| Context | Anywhere, any light, any network | Couch, desk, kiosk | Desk | Desk |
| Information density | Minimum viable | Medium | Medium-high | **High — and users want it** |
| Navigation idiom | Tab bar / bottom sheet / stack | Split view, sidebar | Header nav + breadcrumbs | Menu bar, sidebar, panels, palettes |
| Discoverability need | High (few affordances visible) | High | Medium | Lower (menus are a searchable index) |
| Error cost of a mis-tap | High | Medium | Low | Low |
| Undo expectation | Weak (usually) | Weak | Weak | **Strong — unlimited, always** |
| Offline expectation | High | High | Low-medium | High |
| Governing convention | Apple HIG / Material 3 | Apple HIG / Material 3 | Web conventions + your design system | Platform HIG (macOS/Windows/GNOME/KDE) |

**[DURABLE] The most common cross-form-factor mistake is transposing density.** Shrinking
a desktop layout produces an unusable phone screen; stretching a phone layout produces a
desktop app that insults its users by wasting 70% of the screen and hiding functionality
three taps deep. Density is not a styling decision — it's a claim about how much the user
can and wants to hold in view at once, and that differs by context, not just by pixels.

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Why does this feel confusing/slow/wrong? Perception, memory, attention | §1 |
| Heuristics, usability principles, Norman's model, affordances | §2 |
| Navigation, IA, search, findability, menu structure | §3 |
| Touch vs pointer vs keyboard, gestures, thumb zones, input models | §4 → `ui-ux-interaction-layout-and-visual-design` |
| Layout, grids, responsive, breakpoints, adaptive, foldables | §5 → `ui-ux-interaction-layout-and-visual-design` |
| Typography, color, spacing, elevation, iconography, motion | §6 → `ui-ux-interaction-layout-and-visual-design` |
| Design systems, tokens, component APIs, governance | §7 → `ui-ux-design-systems-platforms-and-accessibility` |
| Platform conventions and how they differ | §8 → `ui-ux-design-systems-platforms-and-accessibility` |
| Accessibility — principles, WCAG, law, testing | §9 → `ui-ux-design-systems-platforms-and-accessibility` |
| Microcopy, error messages, empty states, tone | §10 → `ui-ux-writing-forms-research-and-ethics` |
| Forms, onboarding, checkout, conversion | §11 → `ui-ux-writing-forms-research-and-ethics` |
| Research methods, usability testing, sample size, analytics | §12 → `ui-ux-writing-forms-research-and-ethics` |
| Metrics, HEART, success criteria | §12.4 → `ui-ux-writing-forms-research-and-ethics` |
| Dark patterns, persuasion ethics, regulation | §13 → `ui-ux-writing-forms-research-and-ethics` |
| AI-era interfaces, conversational UI, generative UI | §14 → `ui-ux-writing-forms-research-and-ethics` |
| "Don't do this" | §15 → `ui-ux-reference` |
| "Which is better, X or Y?" | §16 → `ui-ux-reference` (contested) |
| Books, researchers, authoritative sources | §18 → `ui-ux-reference` |
| "Is this still current?" | §17 → `ui-ux-reference` |

---
