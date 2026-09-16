---
name: chat-the-wider-field
description: "Use when evaluating a messenger outside the big three — MLS (RFC 9420) and Wire, WhatsApp's interoperability opening, iMessage PQ3, Threema, Olvid, SimpleX, Session, Nostr, XMPP with OMEMO, Briar, Delta Chat, the dormant and niche ones — or when you need the policy annex that shapes all of them. Companion to the other private-chat-engine skills."
---

# The Wider Field: Everyone Else Worth Knowing, Honestly Assessed

> **Part 5 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §1–§13. Sibling skills:
> `chat-orientation-threat-models-and-landscape` (§0–§5 — the three architectural families, threat-model taxonomy, the comparison matrix, the timeline, the five forces),
> `chat-signal` (§1–§6 — the protocol stack, the organisation and its costs, legal posture, operator and developer perspectives, honest weaknesses),
> `chat-telegram` (§1–§7 — MTProto and the cloud-chat compromise, the Durov prosecution, scale and economics, the bot and Mini-App economy),
> `chat-matrix-and-element` (§1–§6 — federation, Matrix 2.0, the ecosystem and its funding, the homeserver operator handbook, the developer surface),
> `chat-builder-and-operator-playbooks` (§1–§12 — protocol shape, the crypto checklists, the metadata budget, abuse under E2EE, the unglamorous 80%, ops checklists, incident playbooks).
> Section numbers are **per skill**, not shared across the set: each file is a self-contained
> dossier entry. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** state of research 16 September 2026. Architectural descriptions are **stable fundamentals**; project health, ownership, funding and §13's policy annex are **dated specifics**, and several entries here are explicitly flagged as reported-but-thin rather than verified.

> **⚠️ The big three get the press; the interesting engineering and the honest trade-offs live in the long tail. Ordered by architectural significance, not hype.**
>
> **⚠️ GOTCHA** boxes mark where the common mental model is wrong in ways that get people hurt
> or products mis-designed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ MLS IS THE STANDARDS-TRACK ANSWER, AND IT FINALLY SHIPPED**
>    **RFC 9420 is what group messaging cryptography looks like when it is designed rather than accreted. If you are building new, §1 is the first thing to read.**
> 2. **⚠️ THE RADICAL DESIGNS TRADE SOMETHING REAL FOR THEIR PROPERTY**
>    **SimpleX gives up identifiers, Session gives up server accountability for onion routing, Briar gives up the network entirely. Each buys a genuine property at a genuine cost — the entries say which cost.**
> 3. **⚠️ POLICY IS A DESIGN INPUT, NOT A POSTSCRIPT**
>    **§13 is annexed here rather than buried because the rules decide which of these designs are legal to ship, where, and to whom.**

---

The big three get the press; the interesting engineering and the honest trade-offs live in the
long tail. Roughly ordered by architectural significance, not hype.

---

## 1. MLS (RFC 9420) and Wire — the standards track finally ships

**Messaging Layer Security** is the IETF-standardised group-E2EE protocol (RFC 9420, March 2023),
co-initiated by *Wire* with Mozilla, Cisco, Google, Cloudflare, Meta and academia. Its engine is
**TreeKEM**: members sit in a ratchet tree, and a membership change costs **O(log n)** work
instead of the sender-keys/Double-Ratchet's roughly linear cost — which is why Signal-style
groups cap around the low thousands while MLS targets tens of thousands, and why MLS is the
protocol everyone now wants to *converge on*:

- **Wire** — the enterprise messenger (Berlin) — declared **MLS GA across its whole product on
  24 April 2025** ([announcement](https://wire.com/en/blog/wire-mls-is-now-generally-available)),
  replacing its own Proteus protocol; production-tested at 2,000-member channels with 8 devices
  each, calls to 150, and positioning for scale to "hundreds of thousands"
  ([Wire MLS explainer, Dec 2025](https://wire.com/en/blog/messaging-layer-security-mls-explained) ·
  [support pages](https://support.wire.com/hc/en-us/articles/12434725011485-Messaging-Layer-Security-MLS)).
  Wire claims 1,800+ customers and is explicitly chasing German **BSI VS-NfD classified-use
  approval** and EU sovereignty buyers — and frames MLS cipher-suite agility as its post-quantum
  plan ([architecture post, May 2026](https://wire.com/en/blog/secure-communication-architecture-e2ee-mls-identity)).
  ⚠️ "PQ-ready via agility" ≠ "PQ deployed": no shipped PQ ciphersuite is verified in this dossier.
- **Matrix** named MLS a **Matrix 3.0 candidate** (see `chat-matrix-and-element`).
- **Nostr** gained MLS group messaging via the Marmot protocol/NIP-EE (see §8).
- **IETF MIMI** (More Instant Messaging Interoperability) is building cross-provider interop *on*
  MLS: hub/follower server model over mutually-authenticated HTTPS, consent flows, message
  franking for abuse reports, minimal-metadata rooms with pseudonymous credentials, hub-proxied /
  Oblivious-HTTP asset download. **Status: Internet-Drafts, not RFCs** —
  [draft-ietf-mimi-protocol-06 (updated Apr 2026)](https://datatracker.ietf.org/doc/draft-ietf-mimi-protocol/),
  [arch -03 (Jul 2026)](https://www.ietf.org/archive/id/draft-ietf-mimi-arch-03.html),
  [content format -09 (Jul 2026)](https://datatracker.ietf.org/doc/draft-ietf-mimi-content/09/).
  Authors span Cisco, Matrix.org Foundation, Phoenix R&D. Milestones have slipped; knock/invite
  and identity-authentication remain open work.

---

## 2. WhatsApp — the default E2EE of the planet, now partially pried open

Signal-Protocol E2EE by default for ~3 billion users; Noise-pipe transport; sealed-sender-ish
delivery; key-transparency-backed automatic security-code verification (2023); encrypted backups
(opt-in, password/64-digit key). Real caveats that persist: **metadata is Meta's** (no sealed
sender equivalent for graph privacy), account is phone-number-rooted, and "view once"
/disappearing messages are policy features on a surveilled-by-design platform edge.

**The 2024–2026 story is DMA interoperability** (verified):
- Meta, as a designated gatekeeper, must interoperate with third parties at no charge; phase 1
  (1:1 text + files) shipped on deadline, **and in November 2025 the first two third-party
  services — BirdyChat and Haiket — actually went live** with WhatsApp interop in the EEA
  ([EC developer portal](https://digital-markets-act.ec.europa.eu/developer-portal/messaging-interoperability_en) ·
  [Meta's interop explainer (Sep 2024)](https://about.fb.com/news/2024/09/an-update-on-how-were-building-safe-and-secure-third-party-chats-for-users-in-europe/) ·
  [byteiota's launch coverage](https://byteiota.com/whatsapp-eu-interoperability-third-party-messaging-goes-live/)).
- Requirements: Signal Protocol (or equivalent) E2EE with a free Meta sub-license option;
  opt-in user toggle ("Third-party chats"); mobile-only so far; groups due Sep 2025 (rollout
  dragging into 2026), calls due Sep 2027.
- **BEREC's opinion (Mar 2025)** on Meta's reference offers reads like a regulator noticing
  compliance-theatre: no multi-device, manual discovery, vague SLAs, broad Meta termination
  rights, an odd 60-day-EEA-presence rule
  ([BEREC BoR (25) 21](https://www.berec.europa.eu/system/files/2025-03/BoR%20(25)%2021%20BEREC%20Opinion%20on%20Meta's%20reference%20offers.pdf)).
- Neither Signal nor Telegram has requested interop; **May 3, 2026** was the EC's deadline to
  reappraise iMessage's non-designation (outcome not verified in this dossier).
- **Post-quantum: unverified.** One "SignalX-256" article found in research has the hallmarks of
  AI-fabricated content and matches no official announcement; treat WhatsApp as *not* PQ until
  Meta says otherwise credibly.

## 3. Apple iMessage — the post-quantum pacesetter

**PQ3**, announced Feb 2024 ([Apple Security Research](https://security.apple.com/blog/imessage-pq3))
and standard between up-to-date devices since, did the thing Signal hadn't yet done: hybrid
ECC+PQ in the *initial* establishment (Kyber/ML-KEM-1024) **and** ongoing PQ rekeying (Kyber-768
roughly every 50 messages, at least weekly), with classical ECDSA authentication. Apple's level
0–3 taxonomy is now the field's shared vocabulary. Apple's 2025–26 OS generation extended
quantum-safe crypto across TLS/VPN/SSH/CryptoKit ([Apple Platform Security guide](https://support.apple.com/guide/security/quantum-secure-cryptography-apple-devices-secc7c82e533/web)).
Caveats that keep iMessage out of most threat-model recommendations: proprietary stack, iCloud
backups historically undermined E2EE (ADP helps; in Feb 2025 Apple pulled ADP from the UK under
a Home Office order — the restoration state post the UK's reported August 2025 climbdown is
**flagged, not verified**), no Android, closed federation, no operator story whatsoever.
Contact Key Verification (2023) was a genuinely good key-transparency step.

## 4. Threema — the Swiss paid model, now under new ownership

Random 8-digit IDs (no phone/email required), NaCl-class crypto (Curve25519; forward secrecy via
its **Ibex** protocol — which, per the [June 2026 cryptography whitepaper](https://threema.com/assets/documents/threema-cryptography-whitepaper.pdf),
still doesn't cover multi-device configurations), all apps **AGPL open source** with Android
reproducible builds ([open-source page](https://threema.com/en/why-threema/open-source) ·
[GitHub](https://github.com/threema-ch/threema-android)). Sustainable business: paid consumer app +
Threema Work/OnPrem licences. **New in 2026**: acquired by investor Comitis Capital (Jan 2026,
per [heise](https://www.heise.de/en/news/Threema-becomes-quantum-safe-Partnership-with-IBM-Research-11190932.html)),
and a **post-quantum research partnership with IBM Research** announced Feb 2026 (hybrid ML-KEM;
no shipped timetable) ([Threema blog](https://threema.com/en/blog/quantum-secure-future)).
Verdict: solid, honest, unexciting — the "reasonable choice" for Swiss/EU organisations that want
paying-not-spying without self-hosting.

## 5. Olvid — the certification play

French messenger with a **decentralised directory** and no personal-data requirement, the only
messenger holding **ANSSI CSPN** security visas (iOS 2020, Android 2021, evals by Synacktiv —
[Olvid technology page](https://olvid.io/technology/en/)). France mandated it for ministers'
devices in Nov 2023 ([press release](https://www.olvid.io/assets/press-files/CP/2023-11-30_Olvid-CP-CIRCULAIRE-PM_en.pdf)).
In March 2026, amid Kremlin-linked phishing of French officials' Signal/WhatsApp accounts,
Olvid argued the attacks are structurally impossible against its design (no phone tie-in,
mandatory mutual verification, no QR account linking)
([Clubic, 30 Mar 2026](https://www.clubic.com/actualite-606817-la-messagerie-francaise-olvid-dit-pourquoi-contrairement-a-signal-et-whatsapp-elle-n-est-pas-sous-alerte-rouge.html)).
~100k+ users claimed ([EuropeanStack profile](https://europeanstack.com/software/olvid)).

## 6. SimpleX — the no-identifiers radical

The design statement: **no user identifiers at all** — no numbers, usernames, random IDs; every
conversation is reached via pairwise relay queues. SMP relays (Haskell, self-hostable) shuffle
ciphertexts between pairwise queues; XFTP handles chunked encrypted files; optional Tor/onion
transport. That single choice removes account enumeration, contact discovery and much of the
social graph problem — at a UX cost (adding people means out-of-band link exchange).

- **Crypto**: double-ratchet plus, since v5.6 (Mar 2024), **hybrid post-quantum** using
  **sntrup761 parallel-KEM augmentation inside every ratchet step** — break-in *recovery* is PQ,
  not just establishment (their deliberate one-up on PQXDH;
  [announcement](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm/) ·
  [RFC](https://github.com/simplex-chat/simplex-chat/blob/stable/docs/rfcs/2023-09-30-pq-double-ratchet.md);
  sntrup761x25519 itself is now [RFC 9941](https://www.rfc-editor.org/rfc/rfc9941.html), long the
  OpenSSH default).
- **2026 state (verified)**: 3M+ downloads, **480k+ MAU**, 1,000+ community-run servers, $650k in
  donations (incl. Vitalik Buterin), all built on $1.7M over four years
  ([Wefunder launch post, Aug 2026](https://simplex.chat/blog/20260819-simplex-chat-crowdfunding.html) ·
  [ITSFOSS](https://itsfoss.com/news/simplex-chat-investment-drive/) ·
  [crowdfunding page](https://simplex.chat/crowdfunding/)). v6.5 (Apr 2026) shipped **SimpleX
  Channels** (public broadcast: content visible to relays, poster identities private) and a
  **Network Consortium** governance model with Community Credits — an attempt to fund infra
  without ads or surveillance
  ([v6.5 post](https://simplex.chat/blog/20260430-simplex-channels-v6-5-consortium-crowdfunding-freedom-of-speech.html)).
- Operator story: run `smp-server`/`xftp-server`, contribute routing diversity; users bind
  per-contact queues to chosen servers.

## 7. Session — onion-routed messenger on crypto-incentivised nodes

Fork-of-Signal lineage with accounts = keypairs (no phone), messages onion-routed through
~1.5–2k service nodes and stored in **swarms** for offline delivery; **blinded account IDs**
hide recipient keys from nodes. Known weakness: Session's original protocol lacked **perfect
forward secrecy** — hence **Session Protocol v2** (PFS + PQ) in development, planned to debut via
the paid **Session Pro** beta
([Session dev update](https://getsession.org/session-development-update-pro-beta-protocol-v2)).

Verified network history:
- **21 May 2025**: migrated off the Oxen L1 to the **Session Network** with **$SESH on Arbitrum**;
  node staking = 25,000 SESH
  ([migration note](https://getsession.org/migrating-from-the-oxen-network-to-session-network) ·
  [Decrypt coverage](https://decrypt.co/321295/decentralized-messenger-session-goes-live-on-arbitrum-with-sesh-token-launch));
  node upgrade **11.6.0** introduced **Session Router**, a Lokinet rewrite for speed
  ([node upgrade post](https://token.getsession.org/blog/node-upgrade-11-6-0)).
- **2026 near-death**: the Session Technology Foundation paused development and laid off staff;
  community donations rescued it; a 2–3-person team now pushes consolidation into **libsession**,
  the Pro Beta, and Protocol v2 ([The Future of Session](https://getsession.org/the-future-of-session)).
  Read this as: the tech is real, the funding model is crypto-cyclical, caveat emptor.

## 8. Nostr — the pub/sub protocol that accidentally wants to be a messenger

Nostr's native DMs were famously weak (NIP-04 ECDH+AES-CBC: no forward secrecy, metadata in the
clear on relays). The 2025–26 answer is **the Marmot protocol / NIP-EE: MLS groups over Nostr
events** — KeyPackages as addressable events, gift-wrapped membership, FS/PCS semantics from MLS.
Flagship client **White Noise** ([whitenoise-rs](https://github.com/marmot-protocol/whitenoise-rs))
shipped audits (Least Authority), group chat, encrypted media (MIP-04), external signers and SDKs
in five languages through 2026 ([v2026.3.23 notes](https://njump.me/naddr1qqfhw6rfw3jj6mn0d9ek2ttkxgcryd3nx5q3wamnwvaz7tmjv4kxz7fwwpexjmtpdshxuet59upzqawhxlp5wfr3q2wyfpmtxvxj9ppg3fp80x6erghdfk4pcmq8a7hhqvzqqqr4gux747xs) ·
[NIP-EE spec](https://github.com/nostr-protocol/nips/blob/001c516f7294308143515a494a35213fc45978df/EE.md) ·
[Sovereign Engineering podcast #25](https://sovereignengineering.io/podcast/25-white-noise-mls-and-marmot-w-jeff-g)).
Interesting because: transport-agnostic, identity = keypair you already use socially, and MLS
gives it a real group crypto story no one else in web3-adjacent land has.

## 9. XMPP + OMEMO — the original federation, quietly maintained

The most mature self-hosting story of all (Prosody/ejabberd; Snikket for opinionated packaging).
OMEMO (XEP-0384 v0.3) is a Signal-derived double-ratchet E2EE done **purely client-side** — the
server has zero OMEMO knobs ([engineered.at ops account, Feb 2026](https://engineered.at/articles/running-my-own-xmpp-server)).
State of play: **OMEMO 2** (`urn:xmpp:omemo:2`) is rolling out early — Dino via libomemo-c already,
Converse.js's libomemo.js added dual-version support (Jun 2026, with interop vectors and
MAX_SKIP DoS hardening — [release](https://github.com/conversejs/libomemo.js/releases/tag/v2.0.0)),
and Conversations began SCE groundwork with NLnet/EC funding (Apr 2026 —
[announcement](https://nostr.ae/nevent1qqs89ktgxqer2jm9tch3z757qg9tc7xrl728mhh6gepsj9mgsq4dnvqzyqs9q2yr4n39veh6fhsjlahuqxe2dfj5mz0zsdpw653u85nzcj30cj5mgvr));
ecosystem steady (Prosody 13.0.x, ejabberd 26.01, per
[Jan 2026 XMPP newsletter](https://xmpp.org/2026/02/the-xmpp-newsletter-january-2026/)). Federation
metadata caveats: as Matrix, plus weaker defaults (OMEMO coverage is client-dependent).

## 10. Briar — the no-network messenger, in maintenance mode

Bluetooth/Wi-Fi/Tor syncing with zero servers, the Bramble crypto/protocol family, mailbox-based
store-and-forward, forums+blogs; the dissident/journalist tool when the internet is the enemy.
**July 2026: officially in maintenance mode** — security fixes only; the team nearly shut down in
2025 over battery/background-delivery limits and funding, then reversed on community support
([announcement](https://briarproject.org/news/2026-maintenance-mode/)). Desktop is beta (0.6.5,
[Feb 2026](https://briarproject.org/download-briar-desktop/)); Tor/transport stack still updated
(changelog on [GitLab](https://code.briarproject.org/briar/briar/-/wikis/changelog/history)).
Lesson for designers: **pure P2P pays an unforgiving Android battery tax** — OS power management
is a bigger adversary than any censor.

## 11. Delta Chat — email as the federated mesh

Chats over SMTP/IMAP with Autocrypt (OpenPGP) E2EE, "verified group" green-check onboarding,
multi-device, and **webxdc** (in-chat interactive mini-apps shipped as attachments — a genius
offline-friendly extension system used in field deployments). Runs on ordinary mail servers or
fast, simple **chatmail relays**; larger community than Briar per a
[2026 self-hosting comparison](https://selfhostindex.com/compare/briar-project-vs-deltachat-server/).
NLnet-funded. Its unglamorous superpower: it inherits email's reach and censorship tolerances.

## 12. The dead, the dormant, and the niche

- **Wickr**: acquired by AWS (2022); consumer Wickr Me killed end of 2023; AWS wound the
  enterprise product down thereafter (exact end-of-support date unverified here — check AWS's
  notice before citing). The object lesson: "acquired by a hyperscaler" is a winding-down path.
- **Keybase**: Zoom acquisition (2020) effectively froze it; saltpack tooling remains useful.
- **Status / Waku**: the Ethereum-community messenger on libp2p/Waku — small, ideologically
  committed, technically interesting (noise-handshake channels), not a mainstream pick.
- **Line (Letter Sealing), Viber (Rakuten), Kakao, WeChat**: regional defaults with E2EE from
  partial to "on the wrong side of a state firewall of interest" — WeChat is openly
  content-policed and should never appear on a "private" list.
- **Rocket.Chat / Mattermost / Zulip**: team-chat, not *private-chat engines*; E2EE is bolt-on or
  absent. Different dossier.

---

## 13. Policy annex — the rules that shape everything above (verified)

**EU "Chat Control"** is two instruments, and conflating them causes most bad takes:
1. **Temporary derogation (voluntary scanning)**: Regulation **(EU) 2026/1881**, signed 24 Jul
   2026, in force 31 Jul 2026, until 3 Apr 2028. Voluntary scanning for CSAM on **unencrypted**
   services only; **E2EE services are explicitly out of scope**
   ([Council ST-11703-2026](https://data.consilium.europa.eu/doc/document/ST-11703-2026-INIT/en/pdf) ·
   [EU Perspectives](https://euperspectives.eu/2026/07/eu-countries-approve-temporary-chat-control-1-0/) ·
   [The Register, 9 Jul 2026](https://www.theregister.com/security/2026/07/09/meps-fail-to-prevent-chat-control-snoopfest-revival/5269379)).
   The procedurally wild part: a majority of voting MEPs (314) opposed renewal but missed the
   absolute-majority threshold (361); the Council legal service had warned about Charter Art. 7.
2. **Permanent CSA Regulation**: still in trilogue; talks resumed September 2026 under the Irish
   presidency, with Germany the swing vote
   ([WithoutCensorship tracker](https://withoutcensorship.com/chat-control-tracker/) ·
   [closednetwork tracker](https://closednetwork.io/eu-chat-control-the-fight-to-scan-every-private-message-live-tracker/)).
   The contested frontier: mandatory **client-side scanning** of E2EE and upload-moderation
   obligations. Signal and Element have both publicly said they would withdraw from the EU rather
   than comply with client-side scanning.

**The country-by-country pressure map (2025–26, sourced in `chat-signal` and `chat-telegram`)**: Russia (full
WhatsApp block, Telegram throttle, MAX pre-install); Sweden (retention bill targeting E2EE
services; proposed in-force Mar 2026, **vote outcome unverified**); UK (Apple ADP withdrawal
Feb 2025; reported climbdown Aug 2025, restoration state unverified); France (Durov prosecution);
Australia (eSafety suit vs Telegram). The global pattern: states no longer ban privacy — they
regulate the *edges* (retention, discovery, client software, defaults) where E2EE doesn't reach.

---

## Sources (this file)

- Wire/MLS: [MLS GA (24 Apr 2025)](https://wire.com/en/blog/wire-mls-is-now-generally-available) · [MLS explainer (2 Dec 2025)](https://wire.com/en/blog/messaging-layer-security-mls-explained) · [support note](https://support.wire.com/hc/en-us/articles/12434725011485-Messaging-Layer-Security-MLS) · [architecture (6 May 2026)](https://wire.com/en/blog/secure-communication-architecture-e2ee-mls-identity) · [MLS hub](https://wire.com/en/messaging-layer-security) · RFC 9420 (IETF, Mar 2023)
- MIMI: [protocol draft -06 (Apr 2026)](https://datatracker.ietf.org/doc/draft-ietf-mimi-protocol/06/) · [architecture -03 (Jul 2026)](https://www.ietf.org/archive/id/draft-ietf-mimi-arch-03.html) · [content -09 (Jul 2026)](https://datatracker.ietf.org/doc/draft-ietf-mimi-content/09/)
- WhatsApp/DMA: [EC DMA messaging interop portal](https://digital-markets-act.ec.europa.eu/developer-portal/messaging-interoperability_en) · [Meta third-party chats update (Sep 2024)](https://about.fb.com/news/2024/09/an-update-on-how-were-building-safe-and-secure-third-party-chats-for-users-in-europe/) · [BEREC opinion (Mar 2025)](https://www.berec.europa.eu/system/files/2025-03/BoR%20(25)%2021%20BEREC%20Opinion%20on%20Meta's%20reference%20offers.pdf) · [byteiota launch coverage](https://byteiota.com/whatsapp-eu-interoperability-third-party-messaging-goes-live/) · [todoandroid walkthrough](https://en.todoandroid.es/interoperable-chat%3A-how-to-read-messages-from-multiple-apps-in-one/)
- iMessage: [Apple PQ3 (21 Feb 2024)](https://security.apple.com/blog/imessage-pq3) · [Apple quantum-secure crypto guide](https://support.apple.com/guide/security/quantum-secure-cryptography-apple-devices-secc7c82e533/web) · [postquantum.wiki summary](https://postquantum.wiki/imessage-pq3) · [LaMarr field guide](https://fieldguide.lamarrlabs.com/Apple-iMessage-PQ3)
- Threema: [PQ partnership (24 Feb 2026)](https://threema.com/en/blog/quantum-secure-future) · [heise (26 Feb 2026)](https://www.heise.de/en/news/Threema-becomes-quantum-safe-Partnership-with-IBM-Research-11190932.html) · [Cryptography whitepaper (26 Jun 2026)](https://threema.com/assets/documents/threema-cryptography-whitepaper.pdf) · [open source](https://threema.com/en/why-threema/open-source)
- Olvid: [technology/CSPN](https://olvid.io/technology/en/) · [French PM circular press release (Nov 2023)](https://www.olvid.io/assets/press-files/CP/2023-11-30_Olvid-CP-CIRCULAIRE-PM_en.pdf) · [Clubic (30 Mar 2026)](https://www.clubic.com/actualite-606817-la-messagerie-francaise-olvid-dit-pourquoi-contrairement-a-signal-et-whatsapp-elle-n-est-pas-sous-alerte-rouge.html) · [EuropeanStack](https://europeanstack.com/software/olvid)
- SimpleX: [PQ ratchet v5.6 (Mar 2024)](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm/) · [PQ RFC (Sep 2023)](https://github.com/simplex-chat/simplex-chat/blob/stable/docs/rfcs/2023-09-30-pq-double-ratchet.md) · [RFC 9941 (Apr 2026)](https://www.rfc-editor.org/rfc/rfc9941.html) · [v6.5 channels/consortium (30 Apr 2026)](https://simplex.chat/blog/20260430-simplex-channels-v6-5-consortium-crowdfunding-freedom-of-speech.html) · [crowdfunding (19 Aug 2026)](https://simplex.chat/blog/20260819-simplex-chat-crowdfunding.html) · [ITSFOSS](https://itsfoss.com/news/simplex-chat-investment-drive/) · [wefunder page](https://simplex.chat/crowdfunding/)
- Session: [Oxen→Session Network migration](https://getsession.org/migrating-from-the-oxen-network-to-session-network) · [Decrypt (May 2025)](https://decrypt.co/321295/decentralized-messenger-session-goes-live-on-arbitrum-with-sesh-token-launch) · [11.6.0 / Session Router](https://token.getsession.org/blog/node-upgrade-11-6-0) · [Future of Session (2026 rescue)](https://getsession.org/the-future-of-session) · [Pro Beta & Protocol v2](https://getsession.org/session-development-update-pro-beta-protocol-v2)
- Nostr/Marmot: [whitenoise-rs](https://github.com/marmot-protocol/whitenoise-rs) · [v2026.3.23 release notes](https://njump.me/naddr1qqfhw6rfw3jj6mn0d9ek2ttkxgcryd3nx5q3wamnwvaz7tmjv4kxz7fwwpexjmtpdshxuet59upzqawhxlp5wfr3q2wyfpmtxvxj9ppg3fp80x6erghdfk4pcmq8a7hhqvzqqqr4gux747xs) · [NIP-EE](https://github.com/nostr-protocol/nips/blob/001c516f7294308143515a494a35213fc45978df/EE.md) · [SEC podcast #25](https://sovereignengineering.io/podcast/25-white-noise-mls-and-marmot-w-jeff-g) · [Feb 2026 recap](https://nostr.ae/nevent1qqsrkgq9zdaey7ktt8cpapc56m8jwhuzcrgx89k7dlez057g7ag8h0czyp6awd7rguj8zq5ugjrkkvcdy2zz3zjzw7d4jx3w6nd2r3kq0ma0wzlwvf3)
- XMPP: [libomemo.js 2.0.0 (18 Jun 2026)](https://github.com/conversejs/libomemo.js/releases/tag/v2.0.0) · [Gultsch/Conversations (9 Apr 2026)](https://nostr.ae/nevent1qqs89ktgxqer2jm9tch3z757qg9tc7xrl728mhh6gepsj9mgsq4dnvqzyqs9q2yr4n39veh6fhsjlahuqxe2dfj5mz0zsdpw653u85nzcj30cj5mgvr) · [XMPP Newsletter (Jan 2026)](https://xmpp.org/2026/02/the-xmpp-newsletter-january-2026/) · [engineered.at (16 Feb 2026)](https://engineered.at/articles/running-my-own-xmpp-server)
- Briar/Delta Chat: [Briar maintenance mode (9 Jul 2026)](https://briarproject.org/news/2026-maintenance-mode/) · [Briar changelog](https://code.briarproject.org/briar/briar/-/wikis/changelog/history) · [Briar Desktop](https://briarproject.org/download-briar-desktop/) · [selfhostindex comparison](https://selfhostindex.com/compare/briar-project-vs-deltachat-server/)
- Chat Control: [Council doc ST-11703-2026](https://data.consilium.europa.eu/doc/document/ST-11703-2026-INIT/en/pdf) · [EU Perspectives (Jul 2026)](https://euperspectives.eu/2026/07/eu-countries-approve-temporary-chat-control-1-0/) · [The Register (9 Jul 2026)](https://www.theregister.com/security/2026/07/09/meps-fail-to-prevent-chat-control-snoopfest-revival/5269379) · [WithoutCensorship tracker](https://withoutcensorship.com/chat-control-tracker/) · [closednetwork tracker](https://closednetwork.io/eu-chat-control-the-fight-to-scan-every-private-message-live-tracker/)
