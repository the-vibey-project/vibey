---
id: skill-3-focus-and-input-411efcd90c
purpose: 3 focus and input
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-platforms-and-10-foot-ui/SKILL.md
requires: ["skill-2-the-10-foot-ui-ba1b6789fc"]
links: []
---

## §3. Focus and Input

### 3.1 Focus is the architecture

**[DURABLE] On TV, "what is focused" is application state as fundamental as "what page am
I on."** Get this wrong and nothing else matters.

The rules:
1. **Exactly one thing is focused at all times.** Never zero. If a focused element is
   removed, you must explicitly move focus somewhere sensible — this is the single most
   common TV bug, and it manifests as a **completely dead remote**.
2. **The focus indicator must be unmissable** — scale, border, glow, and/or brightness.
   A subtle 1 px outline is invisible at 10 feet. Use at least two visual channels.
3. **Focus must be predictable**: pressing Right then Left should return you where you
   were. Users build a spatial model, and violating it feels broken even when it isn't.
4. **Restore focus on return** — coming back from a detail page must land on the tile you
   left from, not the start of the row.
5. **Set initial focus on every screen**, on the primary action.

### 3.2 Spatial navigation

The engine that decides, given the currently focused element and a direction, what gets
focus next. Approaches:
- **Geometric** — compute the nearest candidate in the direction pressed, using overlap
  and distance heuristics. Flexible, and produces surprising results with irregular layouts.
- **Explicit graph** — declare each element's up/down/left/right neighbours. Predictable;
  tedious; and the right answer for complex screens.
- **Hybrid** — geometric by default with explicit overrides. **What most production apps
  end up doing.**

**[PLATFORM]** Roku's SceneGraph has focus built into the node hierarchy
(`setFocus`, `focusable`); Android TV uses the Android focus system plus
`nextFocusUp/Down/Left/Right` (and Compose for TV's focus APIs); web platforms have
**CSS `spatial-navigation`** in limited/uneven form, so most teams ship a JS library or
their own engine; tvOS has the **focus engine** with focus guides.

> **⚠️ GOTCHA — the classic focus traps.** Focus lands on an off-screen element and the
> user sees nothing move. Focus enters a container it cannot leave. A modal opens without
> capturing focus, so D-pad presses go to the page behind it. A carousel wraps
> inconsistently at the ends. Async content loads and steals focus mid-navigation.
> **Every one of these presents to the user as "the remote stopped working."**

### 3.3 The remote

**[DURABLE] Assume the minimal remote**: D-pad + OK, Back, Home, and maybe
Play/Pause/FF/RW. Everything else is optional and varies by manufacturer, model year, and
whether it's the OEM remote or a universal one.

- **Back must always work and must be predictable.** Back from the player returns to
  detail; back from detail returns to the row; back at the root exits the app (usually
  with a confirmation). **Never trap the user.**
- **Home always exits**, immediately, and you don't get to intervene. Save state
  *continuously*, not on exit.
- **Long-press, key-repeat, and rapid input** — users hold Down to scroll a long row.
  Your list must handle a burst of repeats without falling behind or crashing; debounce
  navigation, and never do heavy work per keypress.
- **Voice** is a first-class input on most platforms (Alexa, Google Assistant, Bixby, and
  in 2026 the LG webOS integrations with Copilot and Gemini) — mostly consumed as
  **deep-link intents** (§7.3 → `smart-tv-playback-drm-and-performance`) rather than in-app.
- **Colour buttons** (red/green/yellow/blue) exist in European broadcast contexts and are
  frequently the right answer for secondary actions there.

### 3.4 Text entry

**[DURABLE] Typing on a TV is so bad that avoiding it is a design requirement, not a
nicety.** Entering a password with a D-pad on an on-screen grid keyboard takes a minute
and fails often. The answers, in order of preference:
1. **Device-code pairing** — show a short code, user enters it on their phone at a URL.
   **This is the standard and correct pattern for sign-in.** Roku's "on-device
   authentication" work is in this family.
2. **Account linking via the platform identity** where offered.
3. **QR code** on screen to hand off to a phone.
4. Voice input for search.
5. Only then, an on-screen keyboard — and if you must, support the platform's native one
   rather than rolling your own.
