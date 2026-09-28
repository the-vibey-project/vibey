---
id: skill-10-voip-and-sip-6a0d7b8a6f
purpose: 10 voip and sip
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-telephony-pstn-ss7-voip-and-caller-id/SKILL.md
requires: ["skill-9-ss7-and-its-security-problem-814eaa106d"]
links: ["skill-11-volte-and-vonr-9d55e4d667"]
---

## §10. VoIP and SIP

**⚠️ The separation that defines it**: ⚠️ **SIP handles signalling — establishing, modifying
and terminating sessions — while RTP carries the actual media, on different ports and often
a different path.**
**⚠️ SDP** negotiates codecs and addresses; ⚠️ **SRTP encrypts media; SIP over TLS protects
signalling.**
**⚠️ Codecs**: ⚠️ **G.711 (uncompressed PSTN quality), G.722 and Opus for wideband —
⚠️ and Opus is the modern default because it adapts across a huge bitrate range and handles
loss gracefully.**
**⚠️ NAT traversal is the perennial engineering pain**: ⚠️ **STUN discovers your public
address, TURN relays when direct connection fails, and ICE tries candidates in order**
(§19 → `comms-webrtc-video-conferencing-team-platforms-and-push`).
**⚠️ Quality metrics**: ⚠️ **latency (⚠️ interactivity degrades noticeably above roughly
150 ms one-way), JITTER (⚠️ absorbed by a jitter buffer, which trades latency for
smoothness), and packet loss — ⚠️ and concealment algorithms mask modest loss surprisingly
well.**
**⚠️ SIP trunking** replaced ISDN for business telephony, ⚠️ **and toll fraud on
misconfigured PBXs remains a live and expensive problem.**

---
