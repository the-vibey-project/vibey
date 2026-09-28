---
id: skill-19-webrtc-b2b3250114
purpose: 19 webrtc
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-webrtc-video-conferencing-team-platforms-and-push/SKILL.md
requires: []
links: ["skill-20-video-conferencing-architecture-11aa124103"]
---

## §19. ⚠️ WebRTC

**⚠️ Real-time audio, video and data in the browser with no plugin** — ⚠️ **and it is the
foundation of most modern conferencing, including products that do not advertise it.**
**⚠️ The pieces**: ⚠️ **getUserMedia for capture, RTCPeerConnection for transport,
RTCDataChannel for arbitrary data (⚠️ over SCTP, giving optionally-reliable
optionally-ordered delivery).**
**⚠️ Signalling is deliberately NOT specified** — ⚠️ **you bring your own, which is why every
WebRTC application needs a server before two browsers can talk.**
**⚠️ ICE, STUN and TURN** (§10 → `comms-telephony-pstn-ss7-voip-and-caller-id`) — ⚠️ **and TURN relaying is the expensive fallback that a
meaningful fraction of connections need.**
> **⚠️ GOTCHA — WebRTC leaks your local and public IP addresses to the page by design**,
> ⚠️ **because ICE candidate gathering requires it.** **⚠️ This has been used for
> de-anonymization and VPN leak detection, and browsers have added mitigations that are
> partial.**

**⚠️ SRTP with DTLS key exchange** means media is always encrypted in transit — ⚠️ **which
is not the same as end-to-end encrypted once an SFU is involved** (§20).

---
