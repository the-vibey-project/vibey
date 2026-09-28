---
id: skill-20-video-conferencing-architecture-11aa124103
purpose: 20 video conferencing architecture
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-webrtc-video-conferencing-team-platforms-and-push/SKILL.md
requires: ["skill-19-webrtc-b2b3250114"]
links: ["skill-21-team-platforms-bca5806717"]
---

## §20. Video Conferencing Architecture

```
⚠️ THE THREE TOPOLOGIES, and the choice explains everything
   ⚠️ MESH  ⚠️ everyone sends to everyone. ⚠️ No server cost,
      and upstream bandwidth explodes past 3-4 participants
   ⚠️ ⚠️ SFU (Selective Forwarding Unit)  ⚠️ THE STANDARD ANSWER.
      Each client sends once; the server FORWARDS streams
      without decoding. ⚠️ Cheap server-side, and the client
      receives many streams
   ⚠️ MCU  ⚠️ the server decodes and composites into one stream.
      ⚠️ Expensive in CPU, and the only option for very weak
      clients
⚠️ SIMULCAST and SVC  ⚠️ send multiple qualities so the SFU can
   forward the appropriate one per receiver — ⚠️ this is what
   makes a gallery view of thirty people work at all
⚠️ ⚠️ THE E2EE PROBLEM  ⚠️ an SFU only forwards, so it CAN work
   with E2EE (insertable streams) — ⚠️ but any server-side
   feature that needs the content (recording, transcription,
   noise suppression, virtual backgrounds computed server-side)
   becomes impossible. ⚠️ THIS TENSION IS WHY MOST CONFERENCING
   IS NOT E2EE BY DEFAULT
   ⚠️ Zoom's 2020 "end-to-end encrypted" marketing was found to
   describe transport encryption, resulting in an FTC
   settlement — ⚠️ the canonical example of §23's confusion
   being commercially convenient
⚠️ THE ACTUAL QUALITY WORK  ⚠️ echo cancellation (⚠️ genuinely
   hard, and why headsets help), noise suppression, automatic
   gain, jitter buffering, loss concealment, bandwidth
   estimation and congestion control
```

---
