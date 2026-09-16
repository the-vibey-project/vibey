---
name: chat-builder-and-operator-playbooks
description: "Use when designing or running a private-chat product — choosing the protocol shape before touching cryptography, the crypto stack as checklists, the metadata budget table every service should fill in, abuse and trust-and-safety under E2EE, the unglamorous 80%, maintained libraries to start from, ops and incident checklists, and budget intuition from public numbers. Companion to the other private-chat-engine skills."
---

# Builder and Operator Playbooks

> **Part 6 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §1–§12. Sibling skills:
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

## 6. Libraries and starting points (all actively maintained as of 2026)

- `signalapp/libsignal-client` (Rust, AGPL) — the canonical stack, SPQR included
  ([repo](https://github.com/signalapp/SparsePostQuantumRatchet)).
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
