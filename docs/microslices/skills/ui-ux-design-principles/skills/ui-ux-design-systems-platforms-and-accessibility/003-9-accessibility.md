---
id: skill-9-accessibility-e78062161b
purpose: 9 accessibility
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-design-systems-platforms-and-accessibility/SKILL.md
requires: ["skill-8-platform-conventions-99ec8151b2"]
links: []
---

## §9. Accessibility

### 9.1 The frame

**[DURABLE] Accessibility is not a feature for a minority.** Roughly 1.3 billion people
live with significant disability; add situational (bright sun, one hand full, noisy room)
and temporary (broken arm, eye dilation) impairments and the addressable population is
everyone. It is also now, in most of the markets a product ships to, **the law**.

**POUR** — the four WCAG principles:
- **Perceivable** — information must be presentable in ways users can perceive (alt text,
  captions, contrast, not-color-alone).
- **Operable** — all functionality via keyboard, enough time, no seizure triggers,
  navigable, adequate targets.
- **Understandable** — readable, predictable, error-preventing and error-explaining.
- **Robust** — works with assistive technologies; valid, semantic markup.

### 9.2 The standards and the law (2026)

| Regime | Standard | Status |
|---|---|---|
| **WCAG 2.2** | Current W3C Recommendation (Oct 2023, updated Dec 2024) | **Approved as ISO/IEC 40500:2025** — enabling more countries to adopt it formally |
| **WCAG 2.1 AA** | The level most laws actually cite | The de facto global legal baseline |
| **WCAG 3.0** | **Working Draft only** (updated March 2026, ~174 requirements; Bronze/Silver/Gold outcome-based scoring replacing A/AA/AAA) | **Not a legal requirement anywhere.** Candidate Recommendation anticipated ~late 2027; final Recommendation realistically 2028–2030. **Will not deprecate WCAG 2.** |
| **EU — European Accessibility Act** | EN 301 549 (currently incorporates WCAG 2.1 AA; **v4.1.1 expected 2026 will move to WCAG 2.2**) | **Enforceable since 28 June 2025** for new products/services. Applies to businesses *anywhere* selling to EU consumers. Existing services have until 28 June 2030; contracts concluded pre-June-2025 until June 2027. Microenterprise exemption (<10 employees AND <€2M turnover) applies to services, not products, and not to non-EU firms serving the EU. Enforcement is per-member-state. |
| **US — ADA Title II** | WCAG 2.1 AA, by DOJ final rule (April 2024) | ⚠️ **Deadlines extended by one year on 20 April 2026** via Interim Final Rule: entities serving **50,000+ → 26 April 2027**; under 50,000 and special districts → **26 April 2028**. The extension changes only the date — the underlying obligation is in force now and people can sue today. |
| **US — ADA Title III** (private business) | No explicit WCAG mandate | Courts apply WCAG anyway; thousands of suits per year (4,600+ in 2025, up ~14% YoY per UsableNet). |
| **US — Section 508** | WCAG 2.0 AA (federal) | |
| **US — Section 504 / HHS** | WCAG 2.1 AA | Deadlines also extended in May 2026: ≥15 employees → 11 May 2027; <15 → 10 May 2028 |
| **UK** | Equality Act; PSBAR for public sector | WCAG 2.1/2.2 AA |

**[DURABLE, practical] Build to WCAG 2.2 AA.** It is a superset of 2.1 AA, so you exceed
every current legal requirement, you're already compliant when EN 301 549 moves to 2.2, and
you're positioned for whatever 3.0 becomes. **Do not wait for WCAG 3.0** — Bronze is
expected to be roughly equivalent to today's 2.2 AA, so conforming now is the head start.

### 9.3 Contrast, and the APCA question

**Current requirement (WCAG 2.x, and therefore the law):** 4.5:1 body text, 3:1 large text
(≥18 pt / 14 pt bold), 3:1 for UI components and graphical objects (SC 1.4.11). The
algorithm is a relative-luminance ratio, polarity-insensitive.

**[CONTESTED — and this one has legal consequences.] APCA** (Advanced Perceptual Contrast
Algorithm) is a perceptual model producing an `Lc` value that accounts for font size,
weight, and polarity. Its proponents argue — with real evidence — that WCAG 2's math
systematically **overstates** contrast when both colors are dark (which is why WCAG-passing
dark-mode palettes can be functionally unreadable) and **understates** some light-background
pairs that are demonstrably readable.

**But:** APCA is a *candidate* method for WCAG 3, which is a Working Draft. No law anywhere
references it. And accessibility practitioners — notably Adrian Roselli, whose April 2026
analysis is the reference on this — warn that advising teams to *replace* WCAG 2 contrast
with APCA creates legal risk, and that WCAG 3's contrast approach is far from settled.

**The defensible position for 2026: conform to WCAG 2 contrast (that's what you'll be
audited against), and optionally *also* check APCA to catch the cases WCAG 2's math misses
— particularly in dark mode.** Choose colors that satisfy both. Do not present APCA
conformance as legal compliance.

Worth internalizing: contrast remains the **most common accessibility failure on the web** —
the WebAIM Million 2026 report found WCAG 2 contrast failures on **83.9% of the top million
home pages**, up from 79.1% the prior year, averaging ~34 low-contrast instances per page.
This is the cheapest defect class to fix and the one most consistently shipped.

### 9.4 The practical checklist

Beyond contrast, the failures that appear on the overwhelming majority of sites are: missing
alt text, unlabeled form inputs, empty links/buttons, and missing document language. Those
four plus contrast are ~95% of automatically-detectable issues.

- **Semantic structure** — real headings in order (no skipping levels), landmarks, lists as
  lists, tables with headers. A screen-reader user navigates by headings; a page of styled
  `<div>`s is a wall.
- **Every input has a persistent, programmatically associated `<label>`.** Placeholder text
  is not a label — it disappears on focus, fails contrast, and breaks autofill and
  translation.
- **Alt text**: describe *purpose*, not appearance. Decorative images get `alt=""`.
  Complex images (charts) need a longer description elsewhere.
- **Focus management**: on route change, on modal open/close, on dynamic content insertion.
  Announce with a live region when appropriate; don't overuse `aria-live="assertive"`.
- **ARIA rule zero: no ARIA is better than bad ARIA.** Use a native `<button>` before you
  build `role="button"` with keyboard handlers.
- **Captions and transcripts** for media; audio description where visual info is essential.
- **Don't rely on hover or precise timing.**
- **Support 200% zoom and 320 px reflow** without horizontal scrolling (SC 1.4.10).

### 9.5 Testing

- **Automated tools (axe, Lighthouse, WAVE, Pa11y) catch roughly a third of issues.** They
  are necessary and radically insufficient. Run them in CI as a floor.
- **Manual keyboard pass**: unplug the mouse, do every task.
- **Screen reader pass**: VoiceOver (macOS/iOS), NVDA or JAWS (Windows), TalkBack (Android),
  Orca (Linux). Test with at least one; behaviours differ meaningfully.
- **Zoom to 200% and 400%**; test with OS-level larger text.
- **Test with users with disabilities.** This is the only method that finds the issues the
  other four can't.
- **⚠️ Accessibility overlay widgets** (one-line JavaScript "compliance" products) have
  repeatedly failed to provide a defense in litigation and drew FTC action; they are widely
  opposed by the accessibility community and by screen-reader users. They are not a
  remediation strategy.
