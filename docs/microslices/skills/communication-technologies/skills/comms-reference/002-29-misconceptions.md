---
id: skill-29-misconceptions-e9870ff0e0
purpose: 29 misconceptions
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-reference/SKILL.md
requires: ["skill-28-what-s-live-checked-august-2026-f490b4bed2"]
links: ["skill-30-numbers-and-dates-41ba844fff"]
---

## §29. Misconceptions

| Misconception | Correction |
|---|---|
| Email From: is verified | ⚠️ **Envelope and header differ. That gap IS spoofing** (§2 → `comms-email-smtp-authentication-and-deliverability`, §5 → `comms-email-smtp-authentication-and-deliverability`) |
| SPF stops spoofing | ⚠️ **It checks the envelope, not what you see. DMARC aligns them** (§5 → `comms-email-smtp-authentication-and-deliverability`) |
| STARTTLS secures email | ⚠️ **Opportunistic and strippable without MTA-STS/DANE** (§2 → `comms-email-smtp-authentication-and-deliverability`) |
| Set DMARC to p=reject immediately | ⚠️ **Read reports first or you'll drop real mail** (§5 → `comms-email-smtp-authentication-and-deliverability`) |
| Deliverability is about content | ⚠️ **Reputation, engagement, complaint rate** (§6 → `comms-email-smtp-authentication-and-deliverability`) |
| PGP encrypts your email | ⚠️ **Not the subject line, not the metadata** (§7 → `comms-email-smtp-authentication-and-deliverability`) |
| SS7 is a legacy curiosity | ⚠️ **Still routes roaming and SMS. No authentication** (§9 → `comms-telephony-pstn-ss7-voip-and-caller-id`) |
| Caller ID shows who's calling | ⚠️ **Asserted by the originator. Trivially forged** (§12 → `comms-telephony-pstn-ss7-voip-and-caller-id`) |
| STIR/SHAKEN proves a call is legitimate | ⚠️ **It attests a carrier's claim about the number** (§12 → `comms-telephony-pstn-ss7-voip-and-caller-id`) |
| 160 characters was a design decision | ⚠️ **It's what fitted in spare signalling capacity** (§13 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| SMS 2FA is fine | ⚠️ **Weakest common factor — SS7, SIM swap. Still beats none** (§9 → `comms-telephony-pstn-ss7-voip-and-caller-id`, §13 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| Non-Latin SMS costs the same | ⚠️ **UCS-2 cuts the limit to 70 chars per segment** (§13 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| MMS is SMS with pictures | ⚠️ **Different system — needs mobile data, recompresses hard** (§14 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| RCS is a carrier standard | ⚠️ **Substantially operated by Google via Jibe** (§15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| RCS was already encrypted | ⚠️ **Google-to-Google only. The standard had none until UP 3.0** (§15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`, §28.1) |
| Telegram is an encrypted messenger | ⚠️ **NOT E2EE by default. Only Secret Chats** (§17 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| WhatsApp backups are encrypted | ⚠️ **Only if you enable it** (§17 → `comms-sms-rcs-signal-protocol-and-messaging-apps`, §23 → `comms-encryption-metadata-interoperability-and-policy`) |
| E2EE protects your conversation | ⚠️ **Not endpoints, backups, metadata or the other party** (§23 → `comms-encryption-metadata-interoperability-and-policy`) |
| Zoom was end-to-end encrypted | ⚠️ **The 2020 claim described transport encryption. FTC settlement** (§20 → `comms-webrtc-video-conferencing-team-platforms-and-push`) |
| Conferencing could easily be E2EE | ⚠️ **Recording, transcription and effects need the content** (§20 → `comms-webrtc-video-conferencing-team-platforms-and-push`) |
| Slack and Teams are private | ⚠️ **Search, retention and eDiscovery require readable content** (§21 → `comms-webrtc-video-conferencing-team-platforms-and-push`) |
| Push notifications are private | ⚠️ **APNs/FCM see the metadata for every app** (§22 → `comms-webrtc-video-conferencing-team-platforms-and-push`) |
| Metadata is less sensitive | ⚠️ **Often more revealing, and usually less legally protected** (§24 → `comms-encryption-metadata-interoperability-and-policy`) |
| Interop mandates improve security | ⚠️ **Bridging can mean the weakest party sets the level** (§25 → `comms-encryption-metadata-interoperability-and-policy`) |
| Client-side scanning breaks encryption | ⚠️ **It circumvents it — reads before the envelope closes** (§26 → `comms-encryption-metadata-interoperability-and-policy`, §28.2) |
| VoIP phones work in a blackout | ⚠️ **Copper powered the handset. IP doesn't** (§27 → `comms-encryption-metadata-interoperability-and-policy`) |
| Encrypted RCS works everywhere now | ⚠️ **Both carriers must support UP 3.0** (§28.1) |
| The EU banned/mandated scanning | ⚠️ **Two separate files. Check which is meant** (§28.2) |

---
