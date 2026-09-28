---
id: skill-12-analytics-and-qoe-e7e6e98f0a
purpose: 12 analytics and qoe
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: ["skill-11-testing-0fb434fb2d"]
links: ["skill-13-cross-platform-strategy-a802491a86"]
---

## §12. Analytics and QoE

Track, at minimum: app launch and time-to-interactive; content start attempts, successes,
and **time to first frame**; **rebuffer count and ratio**; bitrate distribution and
downshift events; **playback failures with error codes**; completion rate and drop-off
curves; navigation paths and where focus was lost; crashes and ANR-equivalents; and — if
ad-supported — ad request/fill/error/completion rates per pod position.

**[DURABLE] Segment every metric by device model and OS version.** A regression that only
affects 2019 Samsungs is invisible in an aggregate and obvious in a segmented view. This
is the single most useful thing you can do with TV analytics, and most teams don't do it.

---
