---
id: skill-28-what-s-live-checked-august-2026-f490b4bed2
purpose: 28 what s live checked august 2026
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-reference/SKILL.md
requires: []
links: ["skill-29-misconceptions-e9870ff0e0"]
---

## §28. What's Live — checked August 2026

### 28.1 ⚠️ Cross-platform encrypted RCS finally shipped
**⚠️ §15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`'s gap closing, and §1 → `comms-email-smtp-authentication-and-deliverability`'s federated-versus-proprietary trade playing out over eight
years.**

- **⚠️ WHAT HAPPENED.** ⚠️ **The GSMA published RCS Universal Profile 3.0 in March 2025, the
  first version to formally define end-to-end encryption for person-to-person RCS, using
  MLS** (§16 → `comms-sms-rcs-signal-protocol-and-messaging-apps`). ⚠️ **The GSMA's technical director framed it as making RCS the first
  large-scale messaging service to support interoperable E2EE between client
  implementations from different providers.**
- **⚠️ IT WENT LIVE 11 MAY 2026**, ⚠️ **in beta with iOS 26.5 and current Google Messages —
  the first time iPhone-to-Android messages could be end-to-end encrypted.** ⚠️ **Encryption
  is on by default where supported, with a lock icon indicating coverage.**
- **⚠️ THE EFF called it a victory**, noting ⚠️ **neither Google, Apple, nor the cellular
  carriers have access to message contents.**
- **⚠️ THE STANDARDIZATION LAG IS THE STORY.** ⚠️ **UP 3.0 was specified in March 2025 and
  took roughly a year to reach a first beta — and one industry commentary notes the GSMA
  had already reached UP 5.0 by then.** ⚠️ **That is §1 → `comms-email-smtp-authentication-and-deliverability`'s federated cost, measured.**

> **⚠️ GOTCHA — three separate caveats, and coverage tends to state only the headline.**
> ⚠️ **FIRST, CARRIER SUPPORT IS REQUIRED ON BOTH ENDS.** ⚠️ **Apple has shipped its side,
> but whether a given conversation is actually encrypted depends on network infrastructure
> Apple neither controls nor publishes a support list for.**
> ⚠️ **SECOND, BUSINESS MESSAGING IS EXCLUDED AND WILL STAY EXCLUDED.** ⚠️ **A2P RCS uses
> transport-layer security, not MLS — and this is architectural rather than an oversight:
> carrier-side compliance filtering, spam detection and regulatory logging require readable
> content** (§15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`, §21 → `comms-webrtc-video-conferencing-team-platforms-and-push`'s same tension).
> ⚠️ **THIRD, METADATA AND BACKUPS REMAIN.** ⚠️ **The EFF's own assessment notes metadata is
> likely still collected, and cloud backups may store conversations unencrypted unless
> Advanced Data Protection is enabled — with Google Messages reportedly encrypting message
> text but not media in backups.** **⚠️ This is §23 → `comms-encryption-metadata-interoperability-and-policy`'s list, arriving on schedule.**

**⚠️ The honest summary**: ⚠️ **a real and large improvement for personal messaging between
platforms, achieved through standardization rather than regulation (§25 → `comms-encryption-metadata-interoperability-and-policy`) — and Signal
remains the stronger choice where metadata matters, which the EFF says explicitly.**

### 28.2 ⚠️ The legal status of message scanning
**⚠️ §26 → `comms-encryption-metadata-interoperability-and-policy`'s debate moving from principle to statute — and the 2026 position is genuinely
tangled.**

- **⚠️ TWO DIFFERENT THINGS SHARE THE NICKNAME, and conflating them is the main source of
  confusion.**
  ⚠️ **"CHAT CONTROL 1.0" is Regulation (EU) 2021/1232 — a temporary derogation from
  ePrivacy PERMITTING (not requiring) providers to voluntarily scan for CSAM. It applies to
  unencrypted services.**
  ⚠️ **"CHAT CONTROL 2.0" is the permanent CSA Regulation proposed in May 2022, which is
  where mandatory detection and client-side scanning have been debated.**
- **⚠️ THE 2026 SEQUENCE ON 1.0.** ⚠️ **Parliament rejected a further extension in March
  2026 and the derogation lapsed on 4 April 2026.** ⚠️ **On 9 July 2026 it was reinstated
  via a fast-tracked Council text, in force until 2028.**
- ⚠️ **The vote mechanics are worth stating precisely, because the headline "Parliament
  passed it" is misleading: 314 MEPs voted to reject and 276 in favour with 17 abstentions,
  but rejection required an ABSOLUTE MAJORITY of 361 — so it passed despite a majority of
  those voting opposing it.** ⚠️ **Reporting indicates an exemption for end-to-end encrypted
  services was adopted.**
- ⚠️ **Notably, Google, Meta, Microsoft and Snap reportedly continued scanning during the
  April–July gap when no legal basis existed.**
- **⚠️ ON 2.0, the permanent regulation**: ⚠️ **the Council dropped the original mandatory
  client-side scanning requirement but retained a permanent voluntary framework,
  age-verification obligations extending to encrypted services, broad risk-mitigation
  obligations, and detection orders for known CSAM via hash-matching on unencrypted
  platforms.** ⚠️ **Trilogue negotiations began December 2025 and the file returns in
  September 2026.**

> **⚠️ GOTCHA — the technical point is independent of the politics and worth stating
> plainly.** ⚠️ **Client-side scanning does not break end-to-end encryption; it inspects
> content on the device BEFORE encryption is applied.** **⚠️ As the Max Planck Society puts
> it, the encryption remains in place but is fundamentally circumvented.**
> ⚠️ **The corresponding point about email is also worth knowing: most email is NOT
> end-to-end encrypted (§7 → `comms-email-smtp-authentication-and-deliverability`), so providers can and already do scan it server-side — which is
> why the debate is specifically about messaging.**
> **⚠️ The industry objection to "voluntary" framings is that risk-mitigation obligations
> can become regulatory pressure to scan, and that a detection-order precedent against E2EE
> services could later be expanded without new primary legislation.**

**⚠️ Elsewhere**: ⚠️ **the UK Online Safety Act gives Ofcom powers that reporting describes
as demanding scanning no encrypted service can satisfy while remaining encrypted — and the
observed provider response has been to WITHDRAW FEATURES from the UK rather than weaken them
globally, which is itself evidence about whether "compliant but still encrypted" is
achievable.**
**⚠️ Sourcing warning, and it is significant.** ⚠️ **Much of the available coverage comes
from campaigning organizations on one side and is written accordingly; the Max Planck
Society and Euronews are the closest to neutral among my sources, and the vote arithmetic is
consistently reported across otherwise-opposed outlets.** ⚠️ **I have described mechanisms
and positions rather than taking one — the technical statement that CSS circumvents rather
than breaks E2EE is a factual claim, not a political one, and both sides accept it.**

---
