---
name: chat-matrix-and-element
description: "Use when running or building on Matrix — the federated protocol and its room/event model, Olm and Megolm, Matrix 2.0 and where it stands, the ecosystem's organisations and funding, the homeserver operator handbook including the European sovereignty deployments, and the developer surface. Companion to the other private-chat-engine skills."
---

# Matrix and Element: The One You Can Actually Operate

> **Part 4 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §1–§6. Sibling skills:
> `chat-orientation-threat-models-and-landscape` (§0–§5 — the three architectural families, threat-model taxonomy, the comparison matrix, the timeline, the five forces),
> `chat-signal` (§1–§6 — the protocol stack, the organisation and its costs, legal posture, operator and developer perspectives, honest weaknesses),
> `chat-telegram` (§1–§7 — MTProto and the cloud-chat compromise, the Durov prosecution, scale and economics, the bot and Mini-App economy),
> `chat-the-wider-field` (§1–§13 — MLS and Wire, WhatsApp, iMessage PQ3, Threema, Olvid, SimpleX, Session, Nostr, XMPP, Briar, Delta Chat, the dead ones, the policy annex),
> `chat-builder-and-operator-playbooks` (§1–§12 — protocol shape, the crypto checklists, the metadata budget, abuse under E2EE, the unglamorous 80%, ops checklists, incident playbooks).
> Section numbers are **per skill**, not shared across the set: each file is a self-contained
> dossier entry. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** state of research 16 September 2026. §1's protocol is **stable fundamentals**. §2 (Matrix 2.0 status), §3 (organisations, money and maintenance) and parts of §4 are **dated specifics** — the funding and maintenance picture in particular changes year to year.

> **⚠️ The only entry here that is an open federated protocol with a real self-hosting story at national scale — and that single fact explains everything else about it.**
>
> **⚠️ GOTCHA** boxes mark where the common mental model is wrong in ways that get people hurt
> or products mis-designed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ FEDERATION MOVES THE COST AND THE METADATA, IT DOES NOT REMOVE THEM**
>    **Running the server is the product, but it also means every homeserver is its own legal and moderation jurisdiction, and federation exposes more metadata to more parties than a single-operator design does.**
> 2. **⚠️ THE OPERATOR HANDBOOK IS THE PERSPECTIVE NOBODY ELSE CAN OFFER**
>    **§4 exists because Signal and Telegram have no equivalent. If you need to be responsible for the infrastructure, this is where the field's only real answer lives.**
> 3. **⚠️ WHO MAINTAINS WHAT IS A LOAD-BEARING QUESTION**
>    **§3 traces the organisations and the money because an open protocol's viability is a funding question as much as a technical one — and adopting it is a bet on that.**

---

Matrix is the only entry in this dossier that is *an open federated protocol with a real
self-hosting story at national scale*. That single fact explains everything else about it: its
politics (European sovereignty wave), its funding struggles (everyone's favourite public good
that nobody wants to fund), and its complexity (federation is genuinely hard).

---

## 1. The protocol (fundamentals — stable)

### 1.1 The data model: rooms as replicated event DAGs
A Matrix "room" is not a file on a server; it is a **partially-replicated directed acyclic graph
of signed JSON events** shared by every homeserver with a participating user. Message events,
membership changes, power levels, redactions — all events in the DAG. Each server keeps the full
history for the rooms it's in and resolves forks with **state resolution** (versioned algorithms;
"state res v2" is the modern one. Room **version 12** — being marched toward default as of mid
2026 — even redefines `room_id` as a hash of the create event, killing server-name dependence for
room identity).

### 1.2 Federation
Servers speak the **Server-Server API** over mutually-authenticated HTTPS with **signing keys**;
discovery via `.well-known` and SRV. Any server can join any joinable room (subject to room ACLs).
Federation is also the privacy caveat: *every participating server stores every (encrypted) event,
room state, and metadata for its users' rooms forever unless retention is configured* — see §4.6.

### 1.3 E2EE: Olm & MegOlm on vodozemac
- **Olm** (double-ratchet 1:1 sessions, X3DH-style one-time keys published to the server) and
  **MegOlm** (an *outbound-only* ratchet for group messages: one symmetric session per sender per
  room, shared to devices via Olm). The reference implementation is now **vodozemac** (Rust,
  formally audited, built with Cryspen) replacing the old C++ libolm in maintained clients.
- **Post-compromise security caveat**: because MegOlm sessions are outbound-only, they don't
  self-heal the way pairwise ratchets do; rotation settings and device-change sharing rules are
  the mitigation. This is a known, documented trade (cheap fan-out vs. weaker PCS).
- **Cross-signing & verification**: users hold master/self-signing/user-signing keys (secured by
  the "secure secret storage"/(4S) backup on the homeserver, protected by a recovery key);
  verification by QR/emoji between devices; the Matrix 2.0-era direction is **invisible
  encryption** — excluding unverified devices and moving toward trust-on-first-use — and the
  **Matrix 3.0 candidate is MLS** (per the [Matrix 2.0 announcement](https://www.matrix.org/blog/2024/10/29/matrix-2.0-is-here/)).

### 1.4 The spec process
MSC (Matrix Spec Change) → Spec Core Team review → spec releases (v1.14 era → **v1.19 expected
imminently**, mid-2026). Amusingly political live question as of 2026: **MSC4504 proposes a
single global "v2" version number** for the whole spec.

---

## 2. Matrix 2.0 (verified) — and where it stands in Sept 2026

Announced/shipped as an *API contract* in October 2024
([Matrix.org](https://www.matrix.org/blog/2024/10/29/matrix-2.0-is-here/)), four pillars:

1. **Simplified Sliding Sync (MSC4186)** — instant login/launch/sync; implemented natively in
   Synapse ≥1.114, deprecating the old sync *proxy*. **Accepted by the Spec Core Team in mid-2026**
   ([TWIM 3 Jul 2026](https://matrix.org/blog/2026/07/03/this-week-in-matrix-2026-07-03/)).
2. **Native OIDC auth (MSC3861)** via the **Matrix Authentication Service (MAS)** — QR-code login,
   external IdPs, modern sessions. (Synapse dropped the experimental MSC3861 phase in favour of
   stable MAS integration in v1.157 cycle, [TWIM 17 Jul 2026](https://matrix.org/blog/2026/07/17/this-week-in-matrix-2026-07-17/)).
3. **MatrixRTC (MSC4143)** — native E2EE group voice/video; built on **Element Call + LiveKit SFU**;
   2026 additions: "slots" (real-time primitives for calls, games, virtual worlds), sticky events,
   a JS MatrixRTC SDK — demos include multiplayer Godot games running over federation
   ([Element blog, FOSDEM 2026](https://element.io/blog/exploring-matrixrtc-real-time-communication-in-rooms/)).
4. **Invisible Encryption** — eliminating the infamous "Unable to Decrypt" errors.

As of September 2026 the Spec Core Team was "aiming to cut" the formal 2.0 release
([TWIM 14 Aug 2026](https://matrix.org/blog/2026/08/14/this-week-in-matrix-2026-08-14/));
Element X clients were shipping 2.0 features incrementally (QR login, user status, live location).

**Federation stats (July 2026)**: ~19,512 known federating servers, **78.8% of them running
Synapse** — the federation's diversity problem in one number.

---

## 3. The ecosystem: organisations, money, and who's maintaining what (verified)

### 3.1 The corporate split
- **Matrix.org Foundation** owns the protocol, spec, and matrix.org homeserver; charity, funded by
  memberships + donations + events + (new in late 2025) **premium accounts on matrix.org**.
- **Element** (formerly New Vector) is the startup founded by Matrix's creators; employs most of
  the core engineering: Synapse, MAS, the Rust/JS SDKs, Element clients, and the matrix.org
  infrastructure itself.
- Per the Foundation's **first public annual report (published March 2026,
  [blog](https://matrix.org/blog/2026/03/annual-report/) ·
  [PDF](https://www.matrix.org/foundation/reports/2025%20Public%20Annual%20Report.pdf))**:
  FY2025 revenue +38%, deficit cut from £910,821 to £310,596; **Automattic's Gold membership alone
  = 50% of revenue**; the report calls the dependence on Element's in-kind donations
  "unsustainable". Earlier milestones: the Feb 2025 ["crossroads" post](https://matrix.org/blog/2025/02/crossroads/)
  ($610K shortfall; public Slack/XMPP/IRC bridges shut), June 2025
  [matrix.org freemium](https://matrix.org/blog/2025/06/funding-homeserver-premium/).

### 3.2 Homeserver implementations
- **Synapse** (Python, increasingly Rust components — client-event serialisation and DB access
  were ported by mid-2026; v1.159-era release candidates marched toward room **v12 as default**):
  the production reference server. Worker-sharded, Postgres-backed, the hardest and most rewarding
  to run at scale.
- **Continuwuity** ([site](https://continuwuity.org/introduction) ·
  [GitHub mirror](https://github.com/continuwuity/continuwuity)): community Rust homeserver,
  forked from the archived **conduwuit**, with weekly-ish releases; easy on modest hardware.
  Fork drama worth knowing: conduwuit's archived README disputes continuwuity's "official
  successor" claim and endorses **Tuwunel** instead — as an operator, evaluate both; migrations
  are conduwuit→continuwuity only (no Synapse/Dendrite path).
- **Dendrite** (Go, second-generation reference) has been in a semi-dormant state since Element
  moved it to the Foundation; do not plan new deployments on it without checking current status.
- Others: Conduit (original Rust project, moribund), Grapevine (stalled).

### 3.3 Clients and bridges
- **Element X** (iOS/Android on matrix-rust-sdk — the strategic client), Element Web/Desktop
  (classic, on matrix-js-sdk), plus the long tail (FluffyChat, Fractal, Cinny, Nheko…).
- Bridges live on the **Application Service API**: the **mautrix** family (Telegram, WhatsApp,
  Signal, Messenger, Slack, Discord…) — Beeper open-sourced its bridge stack; Beeper and Texts
  are now Automattic's (2023–24 acquisitions) — plus hookshot (GitHub/feeds) and matrix-admin
  tooling. Note the Foundation killed the *public* Slack/XMPP/IRC bridges in its 2025 cost cuts;
  self-hosted bridges are unaffected.

### 3.4 The sovereignty wave (verified; the most important customer story in private chat)
- **Germany**: BwMessenger for the Bundeswehr (since Nov 2020, 100k+ active users, BSI-certified
  for VS-NfD) and **BundesMessenger** for the wider public sector (~250,000 users across
  municipalities, agencies, fire services; private federation, BSI-hardened, audited)
  ([Element case study](https://element.io/en/case-studies/bundeswehr) ·
  [Matrix Conf slides Oct 2025](https://2025.matrix.org/slides/slides_9HKYHA.pdf)). Plus
  TI-Messenger for healthcare and openDesk at ZenDiS.
- **France**: Tchap (300k+ public-sector users) and La Suite Numérique, built on Matrix; Olvid
  separately holds the cabinet-level mandate (→ `chat-the-wider-field`).
- **NATO**: NI2CE Messenger (NATO-branded Element fork) via NATO ACT experimentation; **UNICC**
  selected Element (2024); live deployments also credited to US DoD (since 2020), UK MoD, Polish
  and Ukrainian armed forces ([Element's Digital Sovereignty Summit post, Nov 2025](https://element.io/blog/element-at-the-summit-on-european-digital-sovereignty/) ·
  [Computer Weekly, Oct 2025](https://www.computerweekly.com/news/366633894/European-governments-opt-for-open-source-alternatives-to-Big-Tech-encrypted-communications)).
- Catalysts: US sanctions on the ICC, the March 2025 "Signalgate" scandal, and a broad European
  digital-sovereignty push (Merz and Macron keynoted the Berlin summit Element attended).
  France and Germany are even discussing interoperating their national messengers.
- Element's commercial arm is **Element Server Suite (ESS)** — a Kubernetes distribution of the
  stack (Synapse+workers, MAS, Element Web/X, LiveKit, bridges, admin console) with a paid Secure
  tier; Sweden's Försäkringskassan, NATO ACT, UNICC and the EC are credited with
  subscription-based procurement commitments.

---

## 4. Operator handbook: running a homeserver (the perspective nobody else can offer)

### 4.1 Sizing honestly
- Personal/friends server (<50 users): a $6 VPS runs Continuwuity or even Synapse comfortably.
  Synapse RAM pressure comes from *joining big federated rooms*, not your user count — federation
  state, not messages, is the resource hog.
- Community (1–5k users): Synapse on 4–8 vCPU/16–32 GB with Postgres on SSD, media on object
  storage/CF cache; split out `media_repo` and `federation_sender` workers early.
- Institutional: ESS on Kubernetes, or Synapse with full worker separation (sync, client reader,
  federation reader/sender, event persisters, media, background, pusher, appservice) behind a
  smart reverse proxy; Postgres HA; TURN (coturn) + LiveKit for calls.

### 4.2 The ops chores that actually burn people
1. **Postgres tuning & state compression** — `state_groups_state` grows without bound; run the
   rust-synapse-compress-state tool routinely; mind autovacuum.
2. **Media discipline** — set retention (`media_retention: local_media_lifetime`,
   remote_media_lifetime) or watch disk forever; consider matrix-media-repo for dedup/CDN.
3. **Key custody** — your server signing keys *are* your identity in federation. Lose them and
   you rejoin every room. Back them up; rotate carefully (old keys must be kept published for
   history validation).
4. **`server_name` vs server** — use delegation (`.well-known`) so user IDs live on the apex
   domain (alice@example.org) while Synapse runs at matrix.example.org. You cannot cleanly change
   server_name later. This is the #1 forever-decision.
5. **Backups that restore** — Postgres dumps + media store + MAS DB + signing keys + TURN creds;
   *test* restores. E2EE rooms are client-side anyway (4S recovery keys per user — train users on
   recovery keys or accept UTD "can't decrypt" tickets).
6. **Federation hygiene** — room ACLs against abusive servers, `m.room.server_acl` events, and
   subscribing to community policy lists.

### 4.3 Moderation under (mostly) E2EE
On Matrix, E2EE means moderators can't read encrypted content they're not sent — but moderation
is *infrastructure + policy*, not content scanning:
- policy-list subscriptions (**Draupnir** is the successor to Mjolnir — moderation bot watching
  shared ban lists), server ACLs, joins-by-knocking/invite, power levels, slow mode, redactions,
  report forwarding to server admins, and deactivation flows. Public unencrypted rooms are fully
  visible to their homes' admins; homeserver operators bear legal duties for what they host —
  EU-facing communities have DSA obligations worth a compliance read.
- Trust & Safety is real labour: the Foundation's report counts moderation at ~30% on top of the
  matrix.org homeserver's infra cost (~20% of total spend) — one reason Premium exists.

### 4.4 Legal exposure checklist (operator)
you become a CDN *and* a postmaster: retention law in your jurisdiction, lawful-request process
(write one before you need it), CSAM hash-matching duties for public unencrypted content,
copyright complaints, sanctions screening for hosted communities, and GDPR data maps (encrypted
events still carry metadata and IPs in logs — rotate those logs).

### 4.5 Cheat: don't self-host
Element's hosted offerings / ESS Community, etke.cc, un-hooked "matrix for hire" providers —
fine for communities that want sovereignty-lite without the on-call.

### 4.6 The honest privacy critique
Federation sprays *metadata* widely: every server in a room learns membership, timing and the
social graph of everyone in it; E2EE protects content only. Retention defaults are
"keep forever". For dissident-grade threat models, Matrix federation metadata is a real exposure —
SimpleX/Session/Briar exist for a reason (→ `chat-the-wider-field`).

---

## 5. Developer perspective

- **APIs that make it programmable**: the **Client-Server API** (sync, send, E2EE, push),
  the **Application Service API** (bridges/bots with puppeted users), **Widgets**, and the
  server-admin APIs. Spec is open; MSCs are public — you can *propose protocol changes yourself*
  (that's a real differentiator vs. Signal/WhatsApp).
- **SDKs**: `matrix-rust-sdk` (drives Element X; UniFFI bindings into Swift/Kotlin, JS via WASM),
  `matrix-js-sdk` (web-classic), community libs (matrix-nio Python, mautrix-go for bridge-grade
  bots, Trixnity Kotlin…).
- **Build-a-bot in an afternoon**: mautrix-go's appservice framework or matrix-nio + asyncio is
  the fastest route; for business bots, hookshot patterns give you webhooks→rooms.
- **E2EE in your own client**: vodozemac via rust-sdk crypto crate — cross-signing, key backup,
  and verification UX are the hard 80%, all solved for you if you stay on the SDK.
- **Custom real-time**: MatrixRTC SDK "slots" turn rooms into live shared state for games/apps —
  watch this space through 2026–27.
- **Governance literacy**: read the current room version, MSC status and SCT notes before
  building on anything experimental (sliding sync extensions, MSC4505 push for knock/live
  location, etc.). The
  [This Week in Matrix](https://matrix.org/blog/2026/08/14/this-week-in-matrix-2026-08-14/)
  newsletter is the ecosystem's heartbeat.

---

## 6. Verdict

Matrix in 2026 is what email's federation wanted to grow up to be: messy, expensive, politically
essential. If your brief is "we control our infrastructure and our legal jurisdiction," it is —
still, uniquely — the only serious answer among messengers. The costs land on operators and the
Foundation (see the annual report); the benefits land on Europe's governments and everyone who
rejects single-company trust.

---

## Sources (this file)

- Matrix 2.0: [official announcement (29 Oct 2024)](https://www.matrix.org/blog/2024/10/29/matrix-2.0-is-here/)
- This Week in Matrix: [3 Jul 2026 (MSC4186 accepted; 19,512 servers; Synapse 78.8%)](https://matrix.org/blog/2026/07/03/this-week-in-matrix-2026-07-03/) ·
  [17 Jul 2026 (Synapse rustification, MSC4504)](https://matrix.org/blog/2026/07/17/this-week-in-matrix-2026-07-17/) ·
  [14 Aug 2026 (room v12 march, Element X v26.08, SCT release intent)](https://matrix.org/blog/2026/08/14/this-week-in-matrix-2026-08-14/)
- MatrixRTC: [Element blog, FOSDEM 2026 talk (19 Feb 2026)](https://element.io/blog/exploring-matrixrtc-real-time-communication-in-rooms/)
- Foundation finances: [Annual report blog (Mar 2026)](https://matrix.org/blog/2026/03/annual-report/) ·
  [FY2025 Public Annual Report (PDF)](https://www.matrix.org/foundation/reports/2025%20Public%20Annual%20Report.pdf) ·
  ["We're at a crossroads" (Feb 2025)](https://matrix.org/blog/2025/02/crossroads/) ·
  [Premium accounts (Jun 2025)](https://matrix.org/blog/2025/06/funding-homeserver-premium/)
- Deployments: [Element Bundeswehr case study](https://element.io/en/case-studies/bundeswehr) ·
  [BundesMessenger Matrix Conf slides (Oct 2025)](https://2025.matrix.org/slides/slides_9HKYHA.pdf) ·
  [Computer Weekly (31 Oct 2025)](https://www.computerweekly.com/news/366633894/European-governments-opt-for-open-source-alternatives-to-Big-Tech-encrypted-communications) ·
  [Element Digital Sovereignty Summit post (18 Nov 2025)](https://element.io/blog/element-at-the-summit-on-european-digital-sovereignty/) ·
  [Element government positioning post (25 Mar 2025)](https://element.io/blog/advancing-secure-convenient-government-communications-the-case-for-element/)
- Homeservers: [Continuwuity](https://continuwuity.org/introduction) ·
  [continuwuity GitHub mirror](https://github.com/continuwuity/continuwuity) ·
  [archived conduwuit repo (successor dispute)](https://github.com/girlbossceo/conduwuit/)
- vodozemac, matrix-* sdks, mautrix: stable fundamentals from public repos (Element/matrix-org and
  mautrix GitHub orgs); no dated claims relied upon here.
