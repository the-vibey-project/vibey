---
id: skill-21-team-platforms-bca5806717
purpose: 21 team platforms
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-webrtc-video-conferencing-team-platforms-and-push/SKILL.md
requires: ["skill-20-video-conferencing-architecture-11aa124103"]
links: ["skill-22-push-and-notifications-5819ff9e11"]
---

## §21. Team Platforms

**⚠️ Slack** — ⚠️ **channel-based, strong integration model, and the search-and-history
product is arguably what people actually pay for.**
**⚠️ Microsoft Teams** — ⚠️ **wins on bundling rather than on product, and the deep
Office/Graph integration is the genuine differentiator.** ⚠️ **The EU competition case over
bundling with Office led to unbundling commitments.**
**⚠️ Discord** — ⚠️ **built for gaming latency, and its persistent-voice-channel model turns
out to suit communities better than meeting-based tools do.**
**⚠️ The common architecture**: ⚠️ **WebSocket for real-time, an event/message bus, presence
services, and search over history — with the hard engineering in fan-out at scale and in
notification routing** (§22).
> **⚠️ GOTCHA — none of these are end-to-end encrypted, and they generally cannot be.**
> ⚠️ **Search, compliance retention, eDiscovery, DLP and admin export all require the
> provider to read content — and enterprise buyers demand exactly those features.**
> **⚠️ Assume your employer can read anything in them, because that is a contractual product
> feature, not a flaw.**

---
