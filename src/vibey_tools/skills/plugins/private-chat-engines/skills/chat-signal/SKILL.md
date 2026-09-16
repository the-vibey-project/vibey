---
name: chat-signal
description: "Use when working with Signal or the Signal protocol — X3DH and the double ratchet, sealed sender, private contact discovery and SGX enclaves, key transparency, PQXDH and post-quantum ratcheting, the Foundation's cost structure, the legal and political fights, what you can and cannot operate or build, and the weaknesses worth saying out loud. Companion to the other private-chat-engine skills."
---

# Signal: The Reference Implementation of Maximal Trust-Minimisation

> **Part 2 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §1–§6. Sibling skills:
> `chat-orientation-threat-models-and-landscape` (§0–§5 — the three architectural families, threat-model taxonomy, the comparison matrix, the timeline, the five forces),
> `chat-telegram` (§1–§7 — MTProto and the cloud-chat compromise, the Durov prosecution, scale and economics, the bot and Mini-App economy),
> `chat-matrix-and-element` (§1–§6 — federation, Matrix 2.0, the ecosystem and its funding, the homeserver operator handbook, the developer surface),
> `chat-the-wider-field` (§1–§13 — MLS and Wire, WhatsApp, iMessage PQ3, Threema, Olvid, SimpleX, Session, Nostr, XMPP, Briar, Delta Chat, the dead ones, the policy annex),
> `chat-builder-and-operator-playbooks` (§1–§12 — protocol shape, the crypto checklists, the metadata budget, abuse under E2EE, the unglamorous 80%, ops checklists, incident playbooks).
> Section numbers are **per skill**, not shared across the set: each file is a self-contained
> dossier entry. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** state of research 16 September 2026. §1's protocol stack is **stable fundamentals**. §2 (organisation and costs), §3 (legal posture) and §5 (developer surface) are **dated specifics** with inline links — follow them before relying on a figure.

> **⚠️ The most technically rigorous mass-market messenger, and structurally the least operable one: there is no Signal server for you to run.**
>
> **⚠️ GOTCHA** boxes mark where the common mental model is wrong in ways that get people hurt
> or products mis-designed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ EVERYONE ELSE'S CRYPTOGRAPHY IS NAMED AFTER THIS PROTOCOL**
>    **X3DH plus the double ratchet is the baseline WhatsApp, Wire, Matrix's Olm/Megolm and others all build on. Learning it once pays off across the whole field.**
> 2. **⚠️ TRUST MINIMISATION IS THE PRODUCT, NOT JUST THE ENCRYPTION**
>    **Sealed sender, enclave-based contact discovery, zero-knowledge group credentials and key transparency exist because content encryption alone leaves the server knowing who talks to whom. That engineering is the actual differentiator.**
> 3. **⚠️ THERE IS NO OPERATOR STORY, AND THAT IS A DESIGN CHOICE**
>    **§4 is about what to do *instead* — because "just self-host Signal" is not an option, and a plan that assumes it is will fail late.**

---

Signal is both an app and a protocol that everyone else's cryptography is named after. It is the
most technically rigorous mass-market messenger and, structurally, the least operable one: you
can use it, fork it, and study it, but you cannot run it. That constraint *is* the design.

---

## 1. The protocol stack (fundamentals — stable)

### 1.1 Key establishment: X3DH → PQXDH
Classic Signal sessions start with **X3DH** (Extended Triple Diffie–Hellman): each user has a
long-term identity key (IK), publishes a signed pre-key (SPK) and one-time pre-keys (OPKs) to the
server, and an initiator computes up to four DH combinations to bootstrap a shared secret. The
server's pre-key bundles stand in for online presence — that's what makes messaging asynchronous.

**PQXDH** (shipped 2023) keeps X3DH intact and adds a post-quantum KEM: the responder uploads
an ML-KEM-1024 ("last resort") pre-key, the initiator encapsulates against it, and the KEM secret
is mixed with the DH secret so an attacker must break *both*. Crucially it upgrades **initial
secrecy** against harvest-now-decrypt-later without changing the ratchet — ongoing forward
secrecy and post-compromise healing stayed classical until 2025.

### 1.2 The Double Ratchet
Two ratchets stacked:
- a **DH ratchet**: each new message direction change triggers a fresh ephemeral DH, producing
  new root/chain keys — gives **post-compromise security** (self-healing);
- a **symmetric ratchet**: a hash chain inside each direction giving per-message keys — gives
  **forward secrecy** at message granularity.
Out-of-order delivery is handled by caching skipped message keys (bounded by `MAX_SKIP`).

### 1.3 The Triple Ratchet — SPQR goes to production (verified)
In October 2025 Signal announced **SPQR (Sparse Post-Quantum Ratchet)**: a second, quantum-safe
ratchet layered on the Double Ratchet, making the **Triple Ratchet**. Mechanics per
[Signal's announcement (2 Oct 2025)](https://signal.org/blog/spqr/) and the
[research collaborators' write-up (PQShield)](https://pqshield.com/diving-into-signals-new-pq-protocol/):
- uses **ML-KEM-768** for continuous post-quantum forward secrecy *and* post-compromise security;
- ML-KEM ciphertexts/keys are far too big for a chat message, so SPQR **erasure-codes key
  material into ~42-byte chunks** dribbled across ordinary messages (~40 bytes/message overhead)
  — "sparse" because ratchet steps complete opportunistically rather than blocking send;
- rollout is **heterogeneous with safe downgrade**: new clients attach SPQR data old clients
  ignore; downgrade is only permitted during the first messages of a session and is MAC-protected;
  once the fleet has upgraded, Signal plans an update that **enforces SPQR and archives
  non-protected sessions** — the "full coverage" point (future update, implied 2026);
- implementation is Rust, continuously **formally verified**: ProVerif models plus hax/F*
  transpilation run in CI; academic co-design with Cryspen, PQShield, AIST and NYU (papers at
  Eurocrypt '25 and USENIX Security '25; see also Signal's
  [NIST presentation](https://csrc.nist.gov/csrc/media/presentations/2025/post-quantum-ratcheting-for-signal/post-quantum_ratcheting-schmidt_1.14.pdf)
  and [SPIQE 2025 roadmap talk](https://spiqe.cool/2025/slides/SPIQE-Schmidt-Signal.pdf)).
- Open source at [signalapp/SparsePostQuantumRatchet](https://github.com/signalapp/SparsePostQuantumRatchet).

This is the current state of the art: by Apple's own level-0–3 taxonomy, the Triple Ratchet plus
PQXDH is the "Level 3" pattern (PQ-secured establishment *and* ongoing rekeying) that iMessage
PQ3 pioneered at scale in 2024.

### 1.4 Multi-device and identity: Sesame
Signal doesn't expose device-per-device chat; the **Sesame protocol** fan-outs per-device
sessions under a stable identity, and client-side distribution handles device add/remove. From
a user's perspective one conversation; from the protocol's, N parallel ratchets.

### 1.5 Sealed Sender (metadata hardening)
Normally the server must know the sender to route and rate-limit. **Sealed Sender** encrypts even
the sender identity into the envelope body and authenticates delivery via bearer **delivery
tokens** issued at registration (with profile-key-derived tokens for your contacts). Signal's
servers aim to learn only destination timing — the design explicitly limits the metadata the
operator itself could ever hand over.

### 1.6 Zero-knowledge groups (zkgroup)
Group membership, roles and even your own profile attributes are expressed as **anonymous
credentials** (keyed-verification algebraic MAC schemes, CMZ-family, analysed in the
Chase–Perrin–Zaverucha "Signal Groups / ACME" work). The server authenticates *that you're an
authorised member of group X* without learning *who you are* or who else is in it. Same trick
powers private profile storage.

### 1.7 PIN-protected secrets: SVR
**Secure Value Recovery** lets a 4-digit(+) PIN recover your profile/settings/social-graph seeds
on a new phone without Signal being able to read them: SVR2 ran a memory-hard KDF (Argon2-ish)
inside Intel **SGX enclaves** with a Raft-replicated enclave cluster; SVR3 (announced 2023)
hardens the migration path to future enclave platforms. Lesson for builders: "let users restore a
key from a short secret" forces you into threshold/HSM/enclave engineering — there is no cheap
version.

### 1.8 Private contact discovery: CDSI
Who in your address book is on Signal, without Signal learning your address book: the
**Contact Discovery Service (CDSI/CDSv2, "Ice Lake")** does it inside **SGX enclaves over Path
ORAM** so even memory-access patterns leak nothing (Signal's [2017 preview](https://signal.org/blog/private-contact-discovery/),
[2022 ORAM deep-dive](https://signal.org/blog/building-faster-oram/), repo
[signalapp/ContactDiscoveryService-Icelake](https://github.com/signalapp/contactdiscoveryservice-icelake/)).
Caveat for the threat-model file: researchers at V12 found critical object-lifetime bugs in CDSI
that compromised the enclave on the same Azure SGX hardware Signal uses — responsibly disclosed
and fixed ([v12.sh write-up](https://v12.sh/blog/signal)). Enclaves reduce trust; they never
eliminate it. Since **usernames** (Feb 2024), discovery is largely optional — you can hide your
number entirely and be reached by handle or QR.

### 1.9 Backups, at last (verified)
Until 2025 Signal deliberately had *no* cloud backup (Android had local encrypted ones; iOS had
transfer only). On **8 September 2025 Signal shipped opt-in Secure Backups**
([announcement](https://signal.org/blog/introducing-secure-backups/),
[help centre](https://support.signal.org/hc/en-us/articles/9708267671322-Signal-Secure-Backups)):
zero-knowledge, keyed by a 64-char recovery key generated on-device; free tier = all text (100 MiB)
+ last 45 days of media; **paid tier $1.99/month for 100 GB — Signal's first-ever paid feature**
([TechCrunch](https://techcrunch.com/2025/09/08/signal-introduces-free-and-paid-backup-plans-for-your-chats/)).
Backups are stored unlinked from account or payment identity; media is double-encrypted with size
padding; view-once and <24h-disappearing messages are excluded; backups refresh daily. iOS/Desktop
followed Android.

### 1.10 Group calls
1:1 calls are P2P where possible with Signal-operated **relay** fallback (so IPs need not be
exposed); group calls (up to 50) run through a Signal-operated **SFU** that forwards
per-participant E2E-encrypted streams. "Call relay" is a user toggle — IP-vs-latency.

---

## 2. What Signal-the-organisation is (and what it costs) — verified

- **Structure**: the Signal Technology Foundation is a US 501(c)(3), seeded by Brian Acton's
  loan ($50M in 2018, growing to ~$105M, 0% interest, due 2068). President: **Meredith
  Whittaker**; CTO: Ehren Kret. ~50 staff (52 in FY2024).
- **The $50M question**: Signal's own public cost breakdown —
  [*"Privacy is Priceless, but Signal is Expensive"* (Nov 2023)](https://signal.org/blog/signal-is-expensive/)
  — projected ~$50M/yr needed by 2025: ~$14M infrastructure (SMS registration ~$6M, bandwidth
  ~$2.8M of which ~$1.7M is call relaying ~20PB/yr, servers $2.9M, storage $1.3M), ~$19M labour.
- **Actuals (IRS 990s via [ProPublica Nonprofit Explorer](https://projects.propublica.org/nonprofits/organizations/824506840))**:
  FY2024 revenue **$29.4M** (74% contributions), expenses **$38.0M**, deficit **−$8.6M**;
  FY2023 near break-even ($35.8M/$35.8M). The gap explains the paid backup tier.
- **Scale**: 70–100M MAU (Whittaker, NZZ interview April 2025, per
  [SQ Magazine's Signal statistics roundup](https://sqmagazine.co.uk/signal-statistics/)).
- **Subpoena answer**: US federal subpoenas have produced exactly two records — account
  registration timestamp and last-connection date — because Signal retains nothing else
  (documented responses from 2016 and 2021; "by design" rather than policy of the week).

---

## 3. The legal/political posture (verified highlights)

- **Sweden**: a government data-retention bill
  ([draft referral, Nov 2024](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2024/11/utkast-till-lagradsremiss-datalagring-och-tillgang-till-elektronisk-information/);
  proposed in-force March 2026) would oblige encrypted apps to retain data so police can later
  recover chat histories. Whittaker told [SVT (Feb 2025)](https://www.svt.se/nyheter/inrikes/signal-lamnar-sverige-om-regeringens-forslag-pa-datalagring-klubbas):
  Signal will **leave Sweden** rather than comply; the **Swedish Armed Forces themselves opposed
  the bill** while recommending Signal for their own use. A [Global Encryption Coalition letter
  (Apr 2025)](https://www.globalencryption.org/2025/04/joint-letter-on-swedish-data-storage-and-access-to-electronic-information-legislation/)
  with 237 signatories urged rejection. **Vote outcome not confirmed in available sources —
  verify before relying on it.**
- **EU Chat Control**: if client-side scanning of E2EE is ever mandated, "we would leave the
  market" — [Whittaker, Oct 2025](https://cyberinsider.com/signal-vows-to-leave-european-market-if-chat-control-becomes-law/).
  (The July 2026 *temporary* derogation explicitly excludes E2EE services; the fight is the
  *permanent* regulation — see `chat-the-wider-field` §9.)
- **Censorship**: Russia blocked Signal in August 2024 (training-data claim, widely reported at
  the time; not re-verified this run). Signal's censorship-survival toolkit: optional **TLS
  proxies** (community-run, deployed for Iran in 2021), proxy-friendly builds; its earlier
  domain-fronting died in 2018 when AWS/Google killed the trick.
- **Signalgate** (March 2025): US officials accidentally added a journalist to a Signal chat
  planning military strikes. Signal's cryptography did not fail — **endpoint trust, identity
  verification and records-handling did**. The single most instructive operator incident of the
  decade; dissected in `chat-builder-and-operator-playbooks`.

---

## 4. Operator perspective: there is no Signal server to run. Now what?

You cannot self-host Signal. The server source is published (signalapp/Signal-Server, AGPL),
but Signal runs a single global deployment, does not federate, and the clients are built to
talk to Signal's infrastructure. That is intentional: **a single authority makes protocol
upgrades, abuse controls and key-distribution consistency tractable** — Signal explicitly argues
federation ossifies protocols (their 2016 "ecosystem is moving" argument, and it aged well: the
Triple Ratchet shipped globally in weeks; Matrix's E2EE changes take years).

What an operator *can* still do in the Signal ecosystem:

1. **Run censorship-circumvention infrastructure**: a Signal TLS proxy (nginx/docker, domain on
   a TLS-terminating box in a friendly jurisdiction). Low cost, occasional big impact in censored
   countries.
2. **Run hardened-client plumbing**: the community **Molly** fork (hardened Android fork of
   Signal — passphrase-encrypted DB, RAM wiper, reproducible builds; since late 2025 the FOSS
   variant merged into one build with an open-source FCM path, per
   [mollyim/molly](https://github.com/mollyim/mollyim-android) and the
   [Dec 2025 release](https://www.apkmirror.com/apk/mollyim/molly/molly-v7-68-5-1-release/))
   supports **UnifiedPush** instead of Google FCM, via a small Rust server you run:
   [**MollySocket**](https://github.com/mollyim/mollysocket) + a distributor like ntfy or
   NextPush. This eliminates Google's push-timing metadata and the battery hit of WebSocket
   keep-alive ([hands-on guides: kroon.email, Oct 2025](https://kroon.email/site/en/posts/2025/10/molly-unifiedpush/);
   [wirelessmoves.com, Sep 2025](https://blog.wirelessmoves.com/2025/09/from-signal-to-molly-foss-and-unified-push.html)).
3. **Organisational deployment**: Signal is free to deploy across an org, but has **no admin
   controls** (no central user management, no retention enforcement, no audit). Governments that
   need controls (US DoD, UK MoD, Bundeswehr, France) therefore run Matrix/Element instead —
   see `chat-matrix-and-element`. Signal is for *people*; sovereign deployments are for *institutions*.
4. **Threat-informed policy**: disable previews, enable registration lock + screen lock, tune
   disappearing messages, prefer call-relay on sensitive profiles, use username-only discovery,
   and treat linked desktops as extra endpoints (they are).

---

## 5. Developer perspective

- **The library**: [`libsignal-client`](https://github.com/signalapp/libsignal) (Rust, AGPL-3.0)
  is the reference implementation (protocol, zkgroup, SVR, account keys), with Java/Swift/Node
  bindings. Everything from the Double Ratchet to the SPQR machinery is readable — one of the
  best cryptography engineering educations available in any public repo (defensive serialisation,
  constant-time ops, formal-verification CI).
- **Protocol adoption ≠ free licence**: WhatsApp, Google Messages and FB Messenger use Signal
  Protocol under arrangement, not because AGPL is friendly. If you *build on* libsignal-client
  in a proprietary product you inherit AGPL obligations; design accordingly.
- **No official bot/service API**. Signal deliberately has none. The widely used unofficial
  path is `signal-cli` (third-party, links as a device; fine for personal automation, fragile
  and not sanctioned for service development). If your product needs a bot platform, that is
  Telegram's or Matrix's world (→ `chat-telegram`, `chat-matrix-and-element`).
- **What building "on Signal" really means**: you can't; you build *beside* it — Molly-style
  hardened clients, UnifiedPush plumbing, Signal-Protocol-based products with your own server
  (which WhatsApp-scale companies do; see `chat-builder-and-operator-playbooks` for the honest effort budget).
- **Engineering culture to steal**: every protocol change ships with a written design story
  (blog/papers), formal analysis, a heterogeneous-rollout+downgrade-migration plan, and code in
  Rust. The Triple Ratchet rollout (ignore-unknown-fields, MAC-protected downgrade window,
  future enforce-flag) is the canonical pattern for upgrading cryptography across a live fleet.

---

## 6. Honest weaknesses (say them out loud)

- **Phone-number account root** remains (usernames hide it socially, not from Signal).
- **Centralisation**: one foundation, one jurisdiction (US gag orders exist), one funding
  heartbeat — and the 990s show it running lean-to-deficit.
- **No federation, no admin story** — by design, but a real constraint for institutions.
- **Push notification metadata** flows through Apple/Google on stock installs (mitigated by
  content-free notifications and by Molly/UnifiedPush).
- **Desktop attack surface** (Electron) and phone-level compromise remain the practical risks —
  Signal protects the pipe, not the person holding it.
- **SGX dependence** in the trust-minimised services (CDSI, SVR) inherits Intel TEE weaknesses —
  the V12 CDSI compromise shows the risk is empirical, not theoretical.

---

## Sources (this file)

- Signal blog: [SPQR/Triple Ratchet (2 Oct 2025)](https://signal.org/blog/spqr/) · [Secure Backups (8 Sep 2025)](https://signal.org/blog/introducing-secure-backups/) · [Cost breakdown (Nov 2023)](https://signal.org/blog/signal-is-expensive/) · [Private contact discovery (2017)](https://signal.org/blog/private-contact-discovery/) · [ORAM layer (2022)](https://signal.org/blog/building-faster-oram/)
- PQShield: [Triple Ratchet technical dive (2 Oct 2025)](https://pqshield.com/diving-into-signals-new-pq-protocol/)
- NIST/CSRC: [Post-Quantum Ratcheting for Signal slides (2025)](https://csrc.nist.gov/csrc/media/presentations/2025/post-quantum-ratcheting-for-signal/post-quantum_ratcheting-schmidt_1.14.pdf) · [SPIQE 2025 roadmap](https://spiqe.cool/2025/slides/SPIQE-Schmidt-Signal.pdf)
- [signalapp/SparsePostQuantumRatchet](https://github.com/signalapp/SparsePostQuantumRatchet) · [ContactDiscoveryService-Icelake](https://github.com/signalapp/contactdiscoveryservice-icelake/) · [V12 CDSI compromise write-up](https://v12.sh/blog/signal)
- ProPublica: [Signal Technology Foundation 990s (FY2022–2024)](https://projects.propublica.org/nonprofits/organizations/824506840) · [SQ Magazine statistics (Jul 2026)](https://sqmagazine.co.uk/signal-statistics/) · [TechCrunch on cost post (Nov 2023)](https://techcrunch.com/2023/11/17/signal-costs/) · [TechCrunch on backups (Sep 2025)](https://techcrunch.com/2025/09/08/signal-introduces-free-and-paid-backup-plans-for-your-chats/)
- Sweden: [Regeringen draft referral (Nov 2024)](https://www.regeringen.se/rattsliga-dokument/departementsserien-och-promemorior/2024/11/utkast-till-lagradsremiss-datalagring-och-tillgang-till-elektronisk-information/) · [SVT interview (Feb 2025)](https://www.svt.se/nyheter/inrikes/signal-lamnar-sverige-om-regeringens-forslag-pa-datalagring-klubbas) · [The Register (Feb 2025)](https://www.theregister.com/AMP/2025/02/26/signal_will_withdraw_from_sweden/) · [Global Encryption Coalition letter (Apr 2025)](https://www.globalencryption.org/2025/04/joint-letter-on-swedish-data-storage-and-access-to-electronic-information-legislation/) · [CyberInsider on EU stance (Oct 2025)](https://cyberinsider.com/signal-vows-to-leave-european-market-if-chat-control-becomes-law/)
- Molly/UnifiedPush: [mollyim/molly](https://github.com/mollyim/mollyim-android) · [mollysocket](https://github.com/mollyim/mollysocket) · [kroon.email guide (Oct 2025)](https://kroon.email/site/en/posts/2025/10/molly-unifiedpush/) · [wirelessmoves guide (Sep 2025)](https://blog.wirelessmoves.com/2025/09/from-signal-to-molly-foss-and-unified-push.html) · [Molly unification release (Dec 2025)](https://www.apkmirror.com/apk/mollyim/molly/molly-v7-68-5-1-release/)
