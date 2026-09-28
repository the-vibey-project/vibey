---
id: skill-7-lifecycle-deep-linking-and-discovery-fe1da2b1ef
purpose: 7 lifecycle deep linking and discovery
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-playback-drm-and-performance/SKILL.md
requires: ["skill-6-performance-and-memory-5c7ff64553"]
links: []
---

## §7. Lifecycle, Deep Linking, and Discovery

### 7.1 Lifecycle

TV apps get suspended, backgrounded, and killed aggressively, and the user may return
hours later expecting to be exactly where they were.

**[DURABLE] Save playback position continuously — every few seconds — not on exit.** You
will not reliably get an exit callback. The same applies to navigation state, partially
completed forms, and auth state.

**[PLATFORM] Roku's Instant Resume** is a formal version of this, and it is
**becoming a certification requirement**: Roku's Spring 2026 certification update added a
requirement to implement Instant Resume **by 1 October 2026** for apps in the US Streaming
Store meeting the specified streaming criteria. The pattern — return the user to exactly
what they were watching, instantly — is where the whole industry is heading regardless of
platform.

### 7.2 Deep linking

**[DURABLE] Deep linking is not a nice-to-have; it is how the platform's search, voice,
recommendations, and home-screen rows launch your content.** If your app can't be deep
linked, **it is invisible to the platform's discovery surfaces**, which is where a large
share of your traffic would come from.

Two modes to support:
- **Play** — launch directly into playback of a specific asset.
- **Detail/preview** — launch to the content's detail page.

You must handle: cold start with a deep link, warm start with a deep link, an
unentitled user (route to sign-in or upsell **and then continue to the content**), and
content that no longer exists (a graceful message, not a crash).

### 7.3 Content feeds and discovery integration

Each platform ingests a catalogue feed to power search, voice, and home-screen rows.
**[PLATFORM]** Roku Search Feed / Direct Publisher-lineage feeds, Android TV's Watch Next
and channel/program APIs, Apple's TV App integration, Amazon's catalogue ingestion, and
Samsung/LG equivalents. **Getting into these feeds is usually the highest-leverage growth
work available**, and it is unglamorous data-plumbing rather than app development.

**Continue Watching** integration at the *platform* level (not just in-app) is
increasingly expected and, on Roku, tied to the Instant Resume requirement above.
