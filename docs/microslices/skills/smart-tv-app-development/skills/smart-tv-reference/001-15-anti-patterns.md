---
id: skill-15-anti-patterns-0b2cd95d56
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-655fd56384"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Porting a mobile or web UI directly | Wrong density, wrong input model, unreadable at 10 ft | Design for TV from scratch (§2 → `smart-tv-platforms-and-10-foot-ui`) |
| Any UI element that requires hover | No pointer exists | Everything visible in default state |
| Losing focus (zero focused elements) | Presents as a **completely dead remote** | Always move focus explicitly on DOM/node changes (§3.1 → `smart-tv-platforms-and-10-foot-ui`) |
| Subtle focus indicators | Invisible at 10 feet | Scale + border + brightness, at least two channels |
| Not restoring focus on back-navigation | User loses their place every time | Save and restore focus per screen |
| Content outside the ~90% safe area | Physically cut off by overscan | 5% margin all sides (§2.2 → `smart-tv-platforms-and-10-foot-ui`) |
| Body text under ~18–24 px at 1080p | Unreadable | ≥24 px body |
| Pure white on large areas | Painful on a bright panel in a dark room | ~#F0F0F0 or lower |
| Rendering an entire long list | Memory death on TV silicon | Virtualize and recycle (§6.2 → `smart-tv-playback-drm-and-performance`) |
| Full-size images scaled down in the client | Wastes bandwidth, decode memory, and CPU | Server-side exact-size thumbnails |
| Assuming an evergreen browser on Tizen/webOS | A 2024 TV is on Chromium 108; a 2018 TV on 56 | Feature-detect, transpile, test the oldest target (§1.3 → `smart-tv-platforms-and-10-foot-ui`) |
| Version-sniffing the Chromium build | Brittle and wrong | Feature detection |
| Requiring on-screen keyboard sign-in | Miserable; users abandon | Device-code pairing (§3.4 → `smart-tv-platforms-and-10-foot-ui`) |
| Saving playback position only on exit | You won't get the callback | Save continuously |
| No deep-link support | **Invisible to platform search, voice, and recommendation rows** | Support play and detail deep links (§7.2 → `smart-tv-playback-drm-and-performance`) |
| Sequential cold-start network cascade | Blows the time-to-first-frame budget | Parallelize auth/manifest/license |
| Single CENC encryption scheme | `cbcs` vs `cenc` — silently black-screens older devices | Package both, select by capability (§5.1 → `smart-tv-playback-drm-and-performance`) |
| Treating DRM config as set-and-forget | Vendor endpoints and revocation change | Calendar-driven re-checks |
| Client-side entitlement decisions | Trivially bypassed | Enforce server-side (§8.2 → `smart-tv-monetization-certification-and-operations`) |
| Reading the certification checklist before submission | Half of it is architectural | Read it before you design (§10.1 → `smart-tv-monetization-certification-and-operations`) |
| Testing only on flagship hardware | Most users are on the cheap stick | Test on the worst device you support |
| Aggregate-only analytics | Model-specific regressions are invisible | Segment by device model and OS version (§12 → `smart-tv-monetization-certification-and-operations`) |
| Ignoring the platform's caption style settings | Accessibility failure and a cert risk | Honour system settings (§14.1 → `smart-tv-monetization-certification-and-operations`) |
| Mismatched loudness between content and ads | Top-tier user complaint | −23 LUFS / −24 LKFS (§4.2 → `smart-tv-playback-drm-and-performance`) |
| Assuming one Amazon platform | Fire OS and Vega are both live, and APKs don't run on Vega | Plan for both (§1.2 → `smart-tv-platforms-and-10-foot-ui`) |

---
