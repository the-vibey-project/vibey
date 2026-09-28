---
id: skill-12-accessibility-5487f3b0ac
purpose: 12 accessibility
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-extensions-platform-and-standards/SKILL.md
requires: ["skill-11-storage-media-and-capabilities-49308be52b"]
links: ["skill-13-standards-and-interop-0cb5fe5d58"]
---

## §12. Accessibility

**[DURABLE] The browser builds a parallel tree — the accessibility tree — derived from the
DOM, computed styles, and ARIA, and exposes it to platform APIs** (UIA on Windows, NSAccessibility
on macOS, AT-SPI on Linux, AccessibilityNodeInfo on Android).

What that requires: computing role, name (per the **accname** spec — a genuinely intricate
algorithm), state, and relations for every node; keeping the tree updated on mutation;
firing platform events; handling focus order and keyboard interaction; honouring OS
settings (**reduced motion, increased contrast, forced colors, larger text**); and
supporting caret browsing and text ranges.

**⚠️ The accessibility tree lives in the renderer, but assistive technology talks to the
browser process** — so it crosses the security boundary, and in a Site Isolation world it
must be assembled across processes. This is real, under-discussed engineering work, and
it's why accessibility regressions cluster around architectural changes.

---
