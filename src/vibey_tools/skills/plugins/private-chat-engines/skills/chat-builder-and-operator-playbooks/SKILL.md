---
name: chat-builder-and-operator-playbooks
description: "Use when designing or running a private-chat product — choosing the protocol shape before touching cryptography, the crypto stack as checklists, the server components and key custody you have to get right, the pre-launch audit checklist, the metadata budget table every service should fill in, abuse and trust-and-safety under E2EE, the unglamorous 80%, the WebRTC layer behind voice and video, maintained libraries to start from, ops and incident checklists, and budget intuition from public numbers. Companion to the other private-chat-engine skills."
---

# Builder and Operator Playbooks

> **Part 6 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §1–§12 — plus §2.5 (the server you have to write anyway)
> and §5.5 (the WebRTC layer behind voice and video). Sibling skills:
> `chat-orientation-threat-models-and-landscape` (§0–§5 — the three architectural families, threat-model taxonomy, the comparison matrix, the timeline, the five forces),
> `chat-signal` (§1–§6 — the protocol stack, the organisation and its costs, legal posture, operator and developer perspectives, honest weaknesses),
> `chat-telegram` (§1–§7 — MTProto and the cloud-chat compromise, the Durov prosecution, scale and economics, the bot and Mini-App economy),
> `chat-matrix-and-element` (§1–§6 — federation, Matrix 2.0, the ecosystem and its funding, the homeserver operator handbook, the developer surface),
> `chat-the-wider-field` (§1–§13 — MLS and Wire, WhatsApp, iMessage PQ3, Threema, Olvid, SimpleX, Session, Nostr, XMPP, Briar, Delta Chat, the dead ones, the policy annex).
> Section numbers are **per skill**, not shared across the set: each file is a self-contained
> dossier entry. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** state of research 16 September 2026. The checklists and the metadata budget are **stable fundamentals**; §6's library list and §11's budget anchors are **dated specifics**. Assumes the vocabulary of the five sibling skills.

> **⚠️ What you would write in the design doc of a private-chat product, and what you would tape inside the rack of a private-chat deployment.**
>
> **⚠️ GOTCHA** boxes mark where the common mental model is wrong in ways that get people hurt
> or products mis-designed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ CHOOSE THE PROTOCOL SHAPE BEFORE TOUCHING CRYPTO**
>    **§1 is first for a reason. The family decision (centralised E2EE, server-encrypted cloud, federated) constrains every cryptographic choice after it, and reversing it later is a rewrite.**
> 2. **⚠️ EVERY SERVICE MUST FILL IN THE METADATA BUDGET**
>    **§3 is a table, not an essay. If you cannot say what your service learns about who talks to whom and when, you have not designed the privacy — you have only encrypted the content.**
> 3. **⚠️ ABUSE UNDER E2EE IS THE PART EVERYONE FORGETS TO DESIGN**
>    **§4 exists because trust-and-safety cannot be bolted on after the crypto. If the server cannot read content, moderation has to be designed into the product from the start.**

---

This file assumes the five sibling skills. It's organised as **what you would write in the design doc** of a
private-chat product, and **what you would tape inside the rack** of a private-chat deployment.

---

# PART I — THE BUILDER'S PLAYBOOK (software development)

## 1. Choose the protocol shape before touching crypto

| Decision | Options | When each is right |
|---|---|---|
| Group crypto | Double Ratchet + sender keys (Signal/WhatsApp/OMEMO) | groups ≤ few thousand; strongest per-message FS/PCS |
| | **MLS (RFC 9420, TreeKEM)** | large or dynamic groups; standards interop (MIMI, DMA); O(log n) membership ops |
| | MegOlm-style outbound ratchets (Matrix) | cheap fan-out where weak PCS is acceptable and rotation is configured |
| | Pairwise queues, no group crypto (SimpleX) | metadata minimalism above all |
| Delivery | Server-mediated queues | async UX, offline delivery, multi-device |
| | Onion-routed swarms (Session) | network-level unlinkability; latency/storage complexity tax |
| | P2P/direct (Briar, calls) | no server trust; battery/NAT/nat-relay pain |
| Identity | Phone number (Signal/WhatsApp) | viral adoption, abuse control; leaks a government-traceable root |
| | Keypair-only (Session, Nostr, SimpleX) | maximal deniability; discovery UX becomes your problem |
| | Random short ID (Threema) / email (Wire/Delta) | middle paths with existing account rails |

> **⚠️ IF YOU HAVE NO STRONG REASON TO FEDERATE, START CENTRALISED.** The engineering effort is
> roughly **5–10× lower**, the security model is coherent, and one team can ship a protocol upgrade
> to the whole fleet — Signal shipped the Triple Ratchet in weeks; Matrix's E2EE changes take years
> (→ `chat-signal` §4, `chat-matrix-and-element` §2). Federation can be added later; it cannot be
> removed later. It is the right answer for an open communications commons, not for a private system
> where you control the trust model and carry the consequences — and the real bill is state
> replication, cross-server key distribution and split-brain, not the protocol itself
> (→ `chat-matrix-and-element` §4 for what you are signing up to).

## 2. The cryptography stack, as checklists

**Session establishment**
- ☑ Hybrid (classical + PQ) establishment TODAY if you start now — PQXDH (X25519+ML-KEM-1024) is
  the template; harvest-now-decrypt-later is real.
- ☑ One-time pre-key economics: sizing upload cadence vs. exhaustion is a real ops parameter
  (Signal's "last-resort" ML-KEM pre-key pattern is the graceful answer).
- ☑ Auth story: identity keys + fingerprints/safety numbers at minimum; **transparency** (key
  transparency like WhatsApp's auto-verify or Apple's CKV) if you serve billions.

**Ongoing ratchet**
- ☑ DH ratchet for PCS; symmetric chains for FS; bounded skipped-key caches (`MAX_SKIP`) as a
  storage-DoS defence — enforced in the [OMEMO 2 library](https://github.com/conversejs/libomemo.js/releases/tag/v2.0.0)
  for exactly this reason.
- ☑ PQ inside the ratchet, not beside it: Signal's SPQR (ML-KEM-768, erasure-coded 42-byte chunk
  drip) and SimpleX's double-KEM sntrup761 augmentation are the two working designs; choose one
  pattern; do not invent a third.
- ☑ Downgrade discipline: Signal's pattern — unknown-extension tolerance, downgrade only in a
  session's first messages, MAC-protected; then an enforce flag once the fleet converges. Copy it.

**Multi-device**
- ☑ Per-device sessions fanout (Sesame pattern) with client-side membership management; or MLS
  native multi-member model. Never share long-lived identity private keys between devices —
  backup/recovery via sealed storage (4S-style recovery key; SVR-style enclave KDF for
  PIN-recoverable profile keys only if you can staff HSM/enclave engineering — see §5).

**The boring baseline (get these wrong and the ratchet does not save you)**
- ☑ **TLS 1.3** on every client↔server and server↔server hop; never disable certificate verification.
- ☑ **HKDF** for key derivation; **Argon2id** for any password hashing (memory-hard, resists
  GPU/ASIC); **Ed25519** for identity signatures and **X25519** for key exchange.
- ☑ **The OS CSPRNG for all randomness — never a language's default `rand()`.**

> **⚠️ DO NOT IMPLEMENT CRYPTOGRAPHY YOURSELF**
> Use vetted libraries at the highest level of abstraction that solves the problem. **If your code
> contains a mode of operation, an IV, or a padding decision, you are already lower-level than you
> probably need to be.** The primitives are rarely broken; the systems built from them fail
> constantly — implementation bugs, key-management errors, protocol-composition mistakes.

**Key custody — the algorithm choice is easy; where the keys live is where systems fail**
- ☑ **Identity keys**: generated on-device, private half never leaves it, only the public half is
  published. Platform secure storage only — Keychain (iOS), Keystore (Android), libsecret (Linux) —
  **never** the app's sandbox files.
- ☑ **One-time pre-keys**: generated in batches on-device and uploaded; the server dispenses one at
  a time and deletes it after use; the client re-uploads when the pool runs low.
- ☑ **Signed pre-keys**: rotate every few days to weeks; retain the *previous* private key briefly
  for messages already in flight, then delete it.
- ☑ **Session/ratchet state** (chain keys, DH key pair, message counters): never leaves the session;
  persisted encrypted at rest under a key derived from the device passcode, or the next app restart
  loses the conversation.

**Client message pipeline**
- ☑ **Fail closed on the client**: when AEAD verification fails, alert the user and display *nothing*.
  A decryption failure is a possible key-substitution or tampering event, not a rendering bug — and
  "show it anyway with a warning icon" is how that signal gets trained out of users. On send, a
  direction change means the DH ratchet step happens *before* the message key is derived; on both
  paths, persist ratchet state after every message or the next app restart loses the session.

**Before you ship**
- ☑ External security audit by a firm with cryptography *and* messaging experience — not a generic
  application pentest shop.
- ☑ Fuzz the cryptographic code paths.
- ☑ Test **key substitution**: what does the client do when the server returns a different identity
  key? (This is the attack safety numbers and key transparency exist for — prove your client
  notices.)
- ☑ Test **device migration**: does the old device lose access when it should?
- ☑ Test **group membership changes**: can a departed member read new messages? Can a new member
  read old ones? Both are policy decisions — make them deliberately, then test the answer you chose.
- ☑ Test **dropped, reordered and replayed** messages, then **corrupted ciphertext**: authentication
  must fail closed, visibly, and without rendering anything.
- ☑ Penetration-test the server, and re-read the threat model against **what you built** rather than
  what you designed.

## 2.5 The server you have to write anyway (fundamentals — stable)

Whatever the protocol shape, a centralised engine needs the same five pieces — and the privacy of
the product is decided by what each one is allowed to remember:

| Component | Job | What it may keep |
|---|---|---|
| **Account service** | registration, device authentication, account management | account identifier + public identity keys |
| **Pre-key directory** | the X3DH bootstrap: serve one bundle per request | signed pre-key + one-time pre-keys, **each one-time key deleted on use** |
| **Message queue** | hold ciphertext for offline recipients | undelivered messages only — **delete after authenticated client acknowledgement** |
| **Push service** | wake sleeping clients via APNs/FCM | device token; **never message content** |
| **WebSocket / long-poll** | real-time delivery to connected clients | deliver, then dequeue **only** on an authenticated acknowledgement naming the message — a completed write is not receipt |

> **⚠️ IF YOU KEEP MESSAGES AFTER DELIVERY YOU ARE NOT RUNNING A MESSAGE QUEUE, YOU ARE RUNNING A
> MESSAGE ARCHIVE.** Decide which one you are building, then write it into the metadata budget (§3).

**Delivery doctrine.** A socket write that returns is not a message that arrived. The client can
disconnect, crash, or be killed by the OS between your `write()` succeeding and the ciphertext
reaching durable storage on the device — and if you dequeued on the write, the message is now gone
from the server *and* gone from the recipient, permanently, with no error anywhere. Drop it only
when the client says it has it: an **authenticated** acknowledgement, on the authenticated session
that owns that queue, naming the server-assigned ID of the message it persisted. The same rule
governs long-poll — an HTTP 200 on the response proves less than a socket write, not more — so
long-poll delivery is acknowledged on the *next* request, not by the response completing. The price
is that delivery becomes **at-least-once**: a client that persists a message and then loses the
connection before acknowledging will be sent it again. That is the correct trade (a duplicate is a
UI problem, a loss is a broken product), and it is handled, not avoided — give every message a
stable server-assigned ID, have the client discard an ID it has already stored, and make the
acknowledgement itself idempotent so a replayed ack is a no-op rather than an error. Then bound each
queue by age and by depth, or a device that never comes back turns your queue into the archive the
warning above forbids.

**The queue is per device, not per recipient.** The checklist above requires per-device session
fan-out (the Sesame pattern), and delivery has to match it. Hold one queue entry per *device*, and
drop that entry only on an acknowledgement from *that* device. A single recipient-level entry
dequeued on the first acknowledgement to arrive is a message the recipient's phone confirms and
their laptop never receives — and it fails silently in the worst way, because from the server's
side the message was delivered and acknowledged, so nothing anywhere reports an error. So fan a
message out to every registered device of the recipient, track acknowledgement per device, and
retain each copy until that device acknowledges it or its own bound expires. What a device that
registers *later* is owed is a linked-device history policy — a decision you make deliberately in
the metadata budget (§3), not an accident of which device happened to acknowledge first.

**Storage doctrine.** The ideal database holds account registrations, public keys, pre-keys and
undelivered messages. It does **not** hold delivered messages, who-messaged-whom, social graphs or
connection logs. Where a feature forces you to keep some metadata — group membership is the usual
case — keep the minimum and delete it when it stops being needed. Postgres for the relational side,
Redis for the queue; session state belongs to the client, never the server.

☑ **Rate-limit pre-key fetches per account.** An attacker who drains a user's one-time pre-keys
degrades or blocks delivery to them: pre-key exhaustion is a denial-of-service surface, not only a
capacity parameter. §2's "last-resort" pre-key is the graceful half of the answer; the rate limit is
the other half.

## 3. The metadata budget — every service must fill this table

| Datum visible to your server by default | Signal's mitigation | If you can't mitigate it, write it down |
|---|---|---|
| Sender identity on each message | Sealed Sender + delivery tokens | at least encrypt sender outside routing fields |
| Social graph | zero-knowledge groups (zkgroup KVAC credentials), enclave contact discovery (CDSI/PathORAM) | delete-on-delivery policies; retention audits |
| Registration/contact discovery | SGX enclave + ORAM (and its documented enclave-compromise residual risk) | hashing is theatre against nation states; say so |
| Group membership | zkgroup | at least avoid server-readable role metadata |
| Backups | zero-knowledge, unlinked-from-account storage (2025 backups design) | encrypted client-side or *don't offer* backups |
| Push timing/token | content-free pushes; community paths around FCM/APN (Molly+UnifiedPush) | document that Apple/Google see wake-up metadata |
| IPs | call relays; Tor/proxy support | log rotation discipline in writing |

## 4. Abuse & trust-and-safety under E2EE (the part everyone forgets to design)

- **Report flows that carry evidence**: WhatsApp-style "forward last N messages with the report";
  **message franking** (HMAC-style cryptographic "the server really relayed this content"
  receipts) appears in MIMI drafts and Meta's E2EE design.
- **Rate limits without content**: sealed-sender tokens, anonymous credentials for action
  budgets ("N group joins/day, unlinkable").
- **Spam in identifier-free systems** is genuinely hard: SimpleX and Session push burden onto
  link-exchange UX; Signal uses phone-number economics; expect to invent little else.
- **Client-side scanning (Chat Control design space)** is technically "upload moderation" and is
  the policy attack surface right now; decide your policy *before* the law decides it for you
  (Signal's/Element's answer: leave the market; Meta's answer for unencrypted tiers: scan).
- **Ephemeral media safety**: perceptual hashing on-server fails under E2EE by construction; if
  you promise regulators anything else you are writing fiction.

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

## 6. Libraries and starting points (all actively maintained as of 2026)

- `signalapp/libsignal-client` (Rust, AGPL) — the canonical stack, SPQR included
  ([repo](https://github.com/signalapp/SparsePostQuantumRatchet)).
- **libsodium** (C, bindings for every language) — the auxiliary primitives libsignal does not give
  you: AEAD (XChaCha20-Poly1305), X25519 key exchange, Ed25519 signatures, Argon2id password
  hashing, HMAC. Reach for it for everything *around* the ratchet; reach for your platform's TLS
  stack (BoringSSL, OpenSSL, rustls, Secure Transport) for transport, and never disable certificate
  verification to make a test pass.
- MLS: **OpenMLS** (Rust, Phoenix R&D), **mls-rs** (AWS, Rust) — both tracked by Wire/MIMI work.
- Matrix: `matrix-rust-sdk` + vodozemac (crypto incl. cross-signing, 4S backup), `matrix-js-sdk`,
  `mautrix-go` (appservices/bridges), matrix-nio (Python).
- XMPP: libomemo-c (Dino lineage), libomemo.js 2.0 (dual-version OMEMO), aioxmpp/slixmpp.
- SimpleX: simplexmq protocol crates/specs; Telegram: TDLib + Bot API SDKs (→ `chat-telegram`).
- Reference reading that transfers: Signal's engineering blog back-catalogue; RFC 9420; the
  Eurocrypt '25 / USENIX Sec '25 Triple-Ratchet papers; the Matrix spec; Albrecht et al. on
  MTProto for what bespoke protocols cost you.

---

# PART II — THE OPERATOR'S PLAYBOOK

## 7. Pick the architecture by what you're willing to be responsible for

| You want… | Run… | You'll own… |
|---|---|---|
| A zero-ops private chat for family/team | Signal (or Threema paid) | device posture & user training only |
| Sovereign org comms with admin controls | **Element/Synapse or Continuwuity** (Matrix 2.0; or Wire enterprise, self-hosted variants) | infra, keys, GDPR/DSA duties, moderation |
| Public square with scale + bots | Telegram communities | platform policy risk; nothing infra-side |
| Metadata-resistant small group comms | SimpleX (your own relays) | relay uptime, link distribution |
| Censored-population comms | Signal TLS proxies, Session nodes, Delta Chat chatmail, Tor pluggable transports | volunteer infra, rotation discipline |
| Offline/mesh contingencies | Briar (maintenance mode; know it) | pairing logistics |

## 8. The operations checklist (Matrix-flavoured, mostly transferable)

1. **Identity first**: pick the `server_name` apex and delegate via `.well-known`; never migrate
   it later — design your domain story in the first hour.
2. **Key custody**: signing keys in an offline backup before first boot; documented rotation
   procedure; old keys kept publishable.
3. **Storage doctrine**: media retention lifetimes on day one; remote media cache caps;
   state-compression cron (Synapse); Postgres on SSD with autovacuum tuned for state churn.
4. **Capacity**: 2 vCPU/4 GB = personal; 8/32 + worker split = community; k8s + ESS = institution;
   TURN (coturn) and a LiveKit SFU for calls; measure sync latency, not message-send.
5. **AuthN/AuthZ**: MAS (Matrix 2.0 native OIDC) to your IdP; disable open registration or gate
   it behind invites; room defaults: restricted joins; federation allow-lists where lawful.
6. **Moderation stack**: Draupnir + policy lists + report room; admin runbook for illegal-content
   handling (who can redact/deactivate, evidence preservation, DSA/reporting obligations for EU).
7. **Backups & drills**: DB + media + MAS + keys; quarterly restore drills; E2EE key-recovery
   *user education* (4S recovery keys) — most "we lost everything" tickets are client-side.
8. **Observability**: Prometheus/Grafana on sync times, federation queues, room version drift,
   bridge error rates; paging on Postgres replication lag and disk, not on CPU.
9. **Network hygiene**: TLS everywhere incl. federation (8448), modern ciphers, HSTS; egress
   rules for media repo; abuse@ and postmaster@ actually monitored; uptime SLO you can afford.
10. **Legal hygiene**: register a data-protection contact; write the warrant/LEA request SOP
    before the first one arrives; decide logging TTLs (IPs!) deliberately and publish them.

## 9. Operating *communities* on other people's platforms

- **Telegram**: admin permission hygiene, 2FA everywhere above moderator, anti-spam bot layer,
  join-by-approval on raids, export/archive policy (assume platform access disappears or data
  requests land — both have happened in 2024–26), and **never** treat cloud chats as confidential.
- **Signal**: no admin API — governance collapses to social norms + group admin roles + profile
  verification habit (QR/safety numbers at onboarding).
- **Any E2EE tool**: "private app" ≠ "private conversation" — screenshots, device forensic tools,
  subpoenas of *participants*, and the Signalgate class of member error remain. Write conduct
  rules accordingly.

## 10. Incident playbooks worth pre-writing

- **Compromised member device**: rotate (leave/rejoin group to force key change), verify all
  remaining devices, re-run verification ceremonies, audit linked devices.
- **State pressure (block/order)**: pre-positioned proxies and alternate transports, comms-tree
  for users, legal counsel retainer, published transparency-report page.
- **Insider/admin abuse**: power-level audit trail review; split trust (two-person admin ops);
  on Matrix, `m.room.server_acl` changes monitored like firewall rule changes.
- **Crypto upgrade regression**: staged rollout plan cribbed from Signal's heterogeneous
  deployment pattern (Section I.2); never flag-day a federation (Matrix's multi-year rollout of
  room versions is the counterexample that proves the rule).

## 11. Budget intuition from public numbers (verified anchors)

- Signal: **~$38M expenses / 70–100M MAU** (FY2024 filing) — call it ~$0.4–0.6/user/year at
  population scale with ~50 staff and heavy registration/SMS and call-relay costs.
- matrix.org homeserver: infra ≈ 20% of the Foundation's ~£1M-scale spend; moderation roughly
  doubles-to-triples that — [annual report](https://matrix.org/blog/2026/03/annual-report/).
- A community Synapse for 5k users: high-three-figures/low-four-figures a year all-in, plus
  operator time. Session service node: 25,000 SESH stake (token-price exposure). SimpleX relay:
  a VPS and an afternoon — the point of that design.

## 12. The Signalgate lesson, generalised

March 2025: senior US officials coordinated strike planning in a Signal group and accidentally
added a magazine editor. Nothing about Signal failed. Everything around it did: *wrong
channel choice for classified material, no identity verification on join, no records handling,
no device policy*. The operator lesson that transfers to every engine in this dossier:

**E2EE secures the transport between endpoints. It cannot tell you if the endpoints are the
right people, on managed devices, following retention law, or sober.** Organisations answering
that gap in 2026 are buying sovereign Matrix deployments and certified niche messengers
(BwMessenger, Olvid, Wire) — and writing policy, which no protocol ships with.

---

## Sources (this file)

Cross-references throughout to `chat-signal`, `chat-telegram`, `chat-matrix-and-element` and `chat-the-wider-field` carry the dated provenance; additional anchors cited
inline: [libomemo.js 2.0.0 release](https://github.com/conversejs/libomemo.js/releases/tag/v2.0.0),
[Matrix FY2025 annual report](https://matrix.org/blog/2026/03/annual-report/),
[Signal's 990 filings via ProPublica](https://projects.propublica.org/nonprofits/organizations/824506840),
[Signal SPQR announcement](https://signal.org/blog/spqr/),
[Signal Secure Backups](https://signal.org/blog/introducing-secure-backups/),
[SimpleX PQ ratchet](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm/),
[RFC 9420 (MLS)] and [RFC 9941 (sntrup761x25519)](https://www.rfc-editor.org/rfc/rfc9941.html),
[Briar maintenance-mode statement](https://briarproject.org/news/2026-maintenance-mode/).
Stable fundamentals (ratchet mechanics, TreeKEM, federation design) are stated unsourced by design.
