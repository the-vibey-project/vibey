---
id: skill-5-5-voice-video-and-real-time-the-webrtc-layer-you-inherit-fundamentals-stable-6b873310b7
purpose: 5 5 voice video and real time the webrtc layer you inherit fundamentals stable
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-5-the-unglamorous-80-b86b84f9aa"]
links: ["skill-6-libraries-and-starting-points-all-actively-maintained-as-of-2026-c6f821b674"]
---

## 5.5 Voice, video and real-time — the WebRTC layer you inherit (fundamentals — stable)

If the product has calls, it has WebRTC, whether or not anyone says so.

> **⚠️ WEBRTC GIVES YOU ENCRYPTED MEDIA AND NOTHING ELSE. Signalling is deliberately unspecified — your chat server carries the SDP offers/answers and the ICE candidates, or two browsers never meet.**

**The pieces**: `getUserMedia` (camera/mic capture), `RTCPeerConnection` (the encrypted peer
transport), `RTCDataChannel` (arbitrary data over SCTP, optionally reliable, optionally ordered).

**NAT traversal is the hard part.** ICE tries candidate paths; STUN tells a peer its own public
address; **TURN relays when direct connection fails — and a meaningful fraction of calls need it**.
Relay bandwidth is a line item, not a rounding error: Signal's own breakdown puts call relaying at
~$1.7M/yr of ~$2.8M bandwidth, ~20 PB/yr (→ `chat-signal` §2). Budget TURN before you promise calls.

> **⚠️ WEBRTC LEAKS IP ADDRESSES BY DESIGN**
> ICE candidate gathering hands local and public addresses to the page — which is why WebRTC has
> been used for de-anonymisation and VPN-leak detection. Browser mitigations (mDNS for local
> addresses) are partial. **During a call your users' IPs are visible to the other peer** unless you
> force traffic through your own relays, which is exactly what Signal's "always relay calls" toggle
> buys, at latency and bandwidth cost.

**SRTP with DTLS is transport encryption, not E2EE.** Media is always encrypted on the wire with
keys exchanged via DTLS, but the moment an SFU is in the path the SFU can see the media unless you
add E2EE through insertable streams.

| Topology | Who does the work | When it is right |
|---|---|---|
| **Mesh** | everyone sends to everyone | ≤3–4 participants; upstream bandwidth explodes past that |
| **SFU** (selective forwarding unit) | server forwards streams without decoding | the standard answer — Jitsi, LiveKit, mediasoup, Signal's group calls, MatrixRTC |
| **MCU** (multipoint control unit) | server decodes and composites into one stream | only for very weak clients; expensive in CPU, rare in modern systems |

**Simulcast and SVC** — send several qualities so the SFU forwards the appropriate one per
receiver. This is the only reason a gallery view of thirty people works at all.

> **⚠️ THE E2EE PROBLEM WITH CONFERENCING**
> An SFU only forwards, so it *can* work with E2EE (insertable streams: it relays media it cannot
> decode). But every server-side feature that needs the content — recording, transcription, noise
> suppression, server-computed backgrounds — becomes impossible. That tension is why most
> conferencing is not E2EE by default, and why Zoom's 2020 "end-to-end encrypted" marketing
> described transport encryption and ended in an FTC settlement: the canonical case of the four
> meanings of "encrypted" being conflated (→ `chat-orientation-threat-models-and-landscape` §2).

Reference that transfers: [WebRTC for the Curious](https://webrtcforthecurious.com/) and the W3C
WebRTC API spec plus the ICE/STUN/TURN/SRTP/DTLS RFCs.
