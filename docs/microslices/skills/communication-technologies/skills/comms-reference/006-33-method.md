---
id: skill-33-method-83fec8af7e
purpose: 33 method
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-reference/SKILL.md
requires: ["skill-32-quick-reference-fd540a58a0"]
links: []
---

## §33. Method

**§1–§27 → `comms-email-smtp-authentication-and-deliverability`, `comms-telephony-pstn-ss7-voip-and-caller-id`, `comms-sms-rcs-signal-protocol-and-messaging-apps`, `comms-webrtc-video-conferencing-team-platforms-and-push`, `comms-encryption-metadata-interoperability-and-policy` rests on published protocols and long-documented practice** — **SMTP, SIP, the
Signal protocol, MLS, SFU architecture, the SS7 vulnerability literature, and the four-way
distinction in what "encrypted" means.** ⚠️ **None needed verification; RFC 821 is from 1982
and the Signal double ratchet has been publicly specified and independently analyzed for a
decade.**

**Two searches were run in August 2026**, on **encrypted RCS** and **message-scanning law**
— ⚠️ **the first because §15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`'s gap was the largest open hole in mainstream messaging
security and it just closed, the second because §26 → `comms-encryption-metadata-interoperability-and-policy`'s debate has moved from principle into
statute and the current position is widely misreported in both directions.**

**Confidence.** **High** in §23 → `comms-encryption-metadata-interoperability-and-policy` and §1 → `comms-email-smtp-authentication-and-deliverability`, which are the sections I'd most want read.
⚠️ **The four-way distinction between transport encryption, encryption at rest, E2EE and
E2EE-with-verified-keys is the thing that makes marketing claims readable — and the
practical test is worth memorizing: if a provider can show you old messages on a new device
with only a password, it is not end-to-end encrypted.**
⚠️ **§1 → `comms-email-smtp-authentication-and-deliverability`'s federated-versus-proprietary trade is the frame that explains why email and SMS
are insecure and why fixing them takes decades: it is the price of universal reach, not
incompetence.** **⚠️ §24 → `comms-encryption-metadata-interoperability-and-policy`'s point that metadata is often more revealing and less legally
protected than content is the one most people have not internalized.**

**High** on §28.1, anchored on the GSMA's own specification announcement and the EFF's
assessment: ⚠️ **UP 3.0 published March 2025 defining MLS-based E2EE, cross-platform
encrypted RCS live 11 May 2026 in beta.** ⚠️ **The three caveats are the part worth
carrying — carrier support required on both ends, business messaging excluded
architecturally, and metadata and backups untouched — because coverage reliably states the
headline and omits them.**

**Moderate** on §28.2, and deliberately careful. ⚠️ **The vote arithmetic on 9 July 2026 —
314 to reject against a required absolute majority of 361 — is consistently reported across
outlets with opposed editorial positions, which is why I state it precisely: describing this
as "Parliament passed it" is technically true and substantively misleading.**
⚠️ **Much of the available coverage is from campaigning organizations, and I have leaned on
Euronews and the Max Planck Society where possible and flagged the rest.**
**⚠️ I have described mechanisms and positions rather than adopting one.** ⚠️ **The single
technical claim I state flatly — that client-side scanning circumvents rather than breaks
end-to-end encryption — is accepted by advocates on both sides and is the distinction that
makes the rest of the argument legible.**
