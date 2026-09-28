---
id: skill-14-accessibility-privacy-and-regulation-220d7c8731
purpose: 14 accessibility privacy and regulation
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: ["skill-13-cross-platform-strategy-a802491a86"]
links: []
---

## §14. Accessibility, Privacy, and Regulation

### 14.1 Accessibility

**[DURABLE] Captions are a legal requirement in most markets, not a feature.** In the US
this flows from the CVAA and FCC rules for video programming; comparable obligations exist
in the EU (including the European Accessibility Act) and elsewhere.

What that requires: caption rendering that **honours the platform's system caption
settings** (font, size, colour, background, edge style — the user set these once and
expects them everywhere), audio description tracks where the content has them, screen
reader support (VoiceOver on tvOS, TalkBack on Android TV, and each vendor's equivalent),
sufficient contrast, no reliance on colour alone, and — the TV-specific one — **the focus
indicator must be perceivable to users with low vision**, which is a much higher bar than
"there is an outline."

**[VERSIONED]** Accessibility requirements around **caption discovery** are a live 2026
compliance milestone in the US market — check current FCC guidance rather than assuming
the rules you learned earlier still describe the obligation.

### 14.2 Privacy and ACR

**[DURABLE] Smart TVs are among the most privacy-invasive consumer devices in the home**,
and your app operates inside that context whether or not you contribute to it. ACR (§9.3)
samples the screen continuously and identifies content **regardless of source** — including
things that have nothing to do with your app.

**[VERSIONED] Regulation is arriving specifically for this.** The **US Cyber Trust Mark**
programme and **Kentucky HB 692 on ACR data handling** are both named as affecting
privacy-by-design decisions in TV product roadmaps as of 2026 — the latter being an
early example of state-level ACR-specific legislation. Expect more, and expect it to be
inconsistent across jurisdictions.

**Practically, for an app developer**: honour the platform's ad/tracking opt-out signals
(limit-ad-tracking flags, the platform's advertising ID reset), disclose what you collect,
be careful with children's content (COPPA and equivalents apply squarely here), and
remember that **your app's data practices are reviewed at certification**.
