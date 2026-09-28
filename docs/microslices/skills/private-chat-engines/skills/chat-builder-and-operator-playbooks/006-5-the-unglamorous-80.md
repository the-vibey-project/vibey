---
id: skill-5-the-unglamorous-80-b86b84f9aa
purpose: 5 the unglamorous 80
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-4-abuse-trust-and-safety-under-e2ee-the-part-everyone-forgets-to-design-6d5499f734"]
links: ["skill-5-5-voice-video-and-real-time-the-webrtc-layer-you-inherit-fundamentals-stable-6b873310b7"]
---

## 5. The unglamorous 80%

- **Notifications**: content-free payloads; iOS NSE plumbing; Android's FCM hard-dependence vs
  UnifiedPush; battery math (Briar's maintenance-mode obituary paragraph is a cautionary tale).
- **Never put message content in a push payload.** Send a content-free wake-up and let the client
  fetch the message over its own encrypted connection. One OS-level channel (APNs, FCM) multiplexes
  for every app because battery does not permit a persistent connection per app — so Apple and
  Google see arrival timing for essentially everything, and government requests for push records are
  documented. The alternatives are a persistent WebSocket (battery) or background fetch (latency),
  and neither is as reliable as system push; UnifiedPush moves the trust rather than removing it
  (→ `chat-signal` §4).
- **Backups**: the classic E2EE failure (plaintext iCloud/Drive backups defeating the protocol);
  2025's proper templates: Signal's zero-knowledge unlinked backups, WhatsApp's password-sealed
  ADP-style designs.
- **Key/identity UX that humans survive**: QR/emoji verification exists in every client since
  2016 and is used by ~no one — which is precisely why key transparency and TOFU (Matrix 2.0's
  "invisible encryption") are the right industrial answer.
- **Formal verification as CI**: hax/F* extraction + ProVerif models running per-commit is now
  the field's credible bar (libsignal/vodozemac practice), not an academic flourish.
- **Reproducible builds** for Android (Signal/Molly/Threema patterns); supply-chain attestations;
  and a standing plan for "our signing key leaks".
- **Censorship survival**: pluggable transports/proxy hooks, alternate domains, APK sideload
  channels, and a static "get help while we're blocked" site outside your own infra's blast radius.
