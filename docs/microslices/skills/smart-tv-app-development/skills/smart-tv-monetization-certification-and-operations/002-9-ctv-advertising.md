---
id: skill-9-ctv-advertising-3d5d66ee1f
purpose: 9 ctv advertising
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: ["skill-8-monetization-942c9328b2"]
links: ["skill-10-certification-and-submission-ef44880496"]
---

## §9. CTV Advertising

### 9.1 Why this section is long

**[DURABLE] On TV, advertising is not a bolt-on — for AVOD/FAST it is the entire product,
and its technical requirements shape your player architecture.** The commercial context as
of 2026: **US digital video ad spend is projected to exceed $80B and pass 60% of total
TV/video spend for the first time**, and **streaming reached ~48.6% of total US TV
watch-time (Nielsen, May 2026)** — more than broadcast and cable combined.

### 9.2 The plumbing

- **VAST** (Video Ad Serving Template) is the ad-response protocol. **Use VAST 4.x** —
  older versions don't cover the full range of CTV formats and lack the measurement
  capabilities and interactive features modern campaigns need. **VMAP** describes ad break
  scheduling.
- **CSAI (client-side ad insertion)** — the player pauses content, requests an ad, waits,
  plays it, resumes. Simple, and it produces visible seams plus vulnerability to blocking.
- **SSAI (server-side ad insertion, "ad stitching")** — ads are spliced into the stream
  server-side so the client sees one continuous stream. **This is the CTV default**: no
  buffering seam, resistant to ad blockers, and it makes ad transitions feel like
  broadcast. The cost is that **tracking moves server-side** (beacons and quartile events
  fired by the stitcher) and impression accuracy depends on accurate device-ID data.
- **Ad pods** — multiple ads in one break, requiring competitive separation, frequency
  capping, and pod-level decisioning.
- **Universal Ad ID in VAST** solves a real fragmentation problem: without it, the same
  creative uploaded to different platforms gets different IDs, wrecking cross-platform
  reach-and-frequency reporting.
- **OM SDK (Open Measurement)** — IAB Tech Lab's standard for viewability signals; the
  guidance is that **all CTV apps and ad SDKs should integrate it** in supported
  environments.
- **Creative specs** in practice: 16:9, typically ≤ ~200 MB (many platforms prefer under
  150 MB), and the loudness targets in §4.2 → `smart-tv-playback-drm-and-performance`.
- **[PLATFORM]** Roku has its own ad framework (**RAF**) that apps are expected to use
  for measurement compliance.

### 9.3 Measurement, and why it's hard

**[DURABLE] CTV is non-clickable, cookieless, and lives in closed ecosystems.** So
measurement relies on device identifiers, household-level matching, IP signals, and
cross-screen attribution — none of which are as reliable as advertisers want, and all of
which are fragmented across platforms.

**ACR (Automatic Content Recognition)** is the smart-TV-native measurement technology: the
TV samples what's on screen several times per second, converts it to a fingerprint, and
matches it against a reference library — **capturing exposure regardless of input source**
(streaming app, HDMI, antenna, cable). LG Ads and VIZIO's Inscape are the well-known
ACR-derived ad data businesses. **ACR is opt-in and coverage is uneven across device
types**, and it is exactly the capability driving the regulatory attention in §14.2.

**[CONTESTED] Whether CTV measurement is trustworthy.** *For*: fraud rates are lower than
desktop, SSAI logs are server-side and auditable, and ACR gives genuine cross-source
visibility. *Against*: identity is fragmented, location signals are inconsistent, "is
anyone actually in the room?" is unanswerable, and every major OS vendor operates a walled
garden that grades its own homework. **If you're building an ad-supported TV app, budget
for verification partners rather than trusting platform-reported numbers.**

---
