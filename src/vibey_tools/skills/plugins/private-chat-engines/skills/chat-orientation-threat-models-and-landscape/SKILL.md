---
name: chat-orientation-threat-models-and-landscape
description: "Use when orienting in private messaging — the three architectural families and what follows from each, the threat-model questions that decide every other choice, the September 2026 comparison matrix, how the field got here, and the five forces reshaping it. Start here. Companion to the other private-chat-engine skills."
---

# Private Chat Engines: Orientation, Threat Models, and the Landscape

> **Part 1 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §0–§5. Sibling skills:
> `chat-signal` (§1–§6 — the protocol stack, the organisation and its costs, legal posture, operator and developer perspectives, honest weaknesses),
> `chat-telegram` (§1–§7 — MTProto and the cloud-chat compromise, the Durov prosecution, scale and economics, the bot and Mini-App economy),
> `chat-matrix-and-element` (§1–§6 — federation, Matrix 2.0, the ecosystem and its funding, the homeserver operator handbook, the developer surface),
> `chat-the-wider-field` (§1–§13 — MLS and Wire, WhatsApp, iMessage PQ3, Threema, Olvid, SimpleX, Session, Nostr, XMPP, Briar, Delta Chat, the dead ones, the policy annex),
> `chat-builder-and-operator-playbooks` (§1–§12 — protocol shape, the crypto checklists, the metadata budget, abuse under E2EE, the unglamorous 80%, ops checklists, incident playbooks).
> Section numbers are **per skill**, not shared across the set: each file is a self-contained
> dossier entry. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** state of research 16 September 2026. **Stable fundamentals** (protocol mechanics — how a double ratchet works does not go stale) are separated throughout from **dated specifics** (verified against live sources in September 2026, with links and dates inline) and **reported-but-thin items**, which are flagged as such and never dressed up as verified. §3's matrix and §5's forces expire fastest.

> **⚠️ Every private chat engine falls into one of three architectural families, and almost every design decision — cost, privacy, failure modes, what you can operate or build — follows from which one it is in.**
>
> **⚠️ GOTCHA** boxes mark where the common mental model is wrong in ways that get people hurt
> or products mis-designed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE FAMILY DETERMINES THE OPERATOR STORY**
>    **Centralised E2EE (Signal, WhatsApp, Wire, Threema, iMessage, Olvid): you cannot self-host, only use or build alongside. Centralised server-encrypted cloud (Telegram): you operate communities and bots on someone else's infrastructure. Federated (Matrix, XMPP, Session, SimpleX, Briar, Delta Chat, Nostr): running the infrastructure *is* the product.**
> 2. **⚠️ CONVENIENCE REQUIRES SOMEONE TO SEE MORE**
>    **Sync, search, discovery, notifications, group management, abuse reporting — each is metadata or content visibility somebody has to be trusted with, or an engineering trick that avoids it. That trade never goes away; it only moves.**
> 3. **⚠️ WITH CONTENT ALREADY OPAQUE, THE FIGHT IS OVER METADATA**
>    **Who talked to whom, when, how often. Sealed sender, private contact discovery, key transparency and enclave attestation are all attempts to shrink it — and §2's taxonomy is how you decide which of them you actually need.**

---

> **Provenance note.** This dossier separates three kinds of claim: **stable fundamentals** (protocol
> mechanics — how a double ratchet works doesn't go stale), **dated specifics** (verfied against live
> sources in September 2026, with links and dates inline), and **reported-but-thin items** (flagged as
> such, never dressed up as verified). Training-data knowledge extends to January 2026; everything
> after that is sourced or flagged. If a claim matters to a real decision, follow the link.
>
> **State of research:** 16 September 2026.

---

## 0. How to use this dossier

Six skills:

| Skill | What it covers |
|---|---|
| **`chat-orientation-threat-models-and-landscape`** (this one) | The three architectural families, threat-model taxonomy, comparison matrix, timeline |
| **`chat-signal`** | Signal — protocol stack, organisation, cost economics, legal fights, what you can (and can't) operate or build |
| **`chat-telegram`** | Telegram — MTProto, the cloud-chat compromise, the bot/Mini-App economy, the post-arrest compliance turn |
| **`chat-matrix-and-element`** | Matrix/Element — federation, homeserver operations, Matrix 2.0, the European sovereignty wave |
| **`chat-the-wider-field`** | The wider field — Wire/MLS, WhatsApp, iMessage PQ3, Threema, Olvid, SimpleX, Session, XMPP, Briar, Delta Chat, Nostr, the dead ones |
| **`chat-builder-and-operator-playbooks`** | The two perspectives — a builder's playbook and an operator's playbook, with checklists |

Reading order: this skill first; then the four engine skills in any order;
`chat-builder-and-operator-playbooks` last, because it assumes the vocabulary.

---

## 1. The three architectural families

Every private chat engine falls into one of three families. Almost every design decision —
cost, privacy, failure modes, what you as an operator or developer can do — follows from which
family it belongs to.

### Family A: Centralised end-to-end-encrypted
*Signal, WhatsApp, Wire, Threema, iMessage, Olvid*

One company runs the only servers it will talk to. Encryption keys live on devices; the server
mostly shuttles ciphertext. **The operator story is non-existent**: you cannot self-host these;
you can only be a user or an ecosystem developer. The privacy battle is fought on **metadata**
(who talked to whom, when) because content is already opaque to the server. The engineering
battle is fought on **key management at scale** (multi-device, recovery, backups) and
**trust minimisation** (enclaves, zero-knowledge credentials, sealed sender, key transparency).

### Family B: Centralised, server-encrypted cloud
*Telegram*

Everything is encrypted in transit and at rest on Telegram's servers, but **Telegram holds the
keys** — that's what makes multi-device sync, 200,000-member groups, searchable history and
channels possible. E2EE ("Secret Chats") exists only for 1:1 mobile chats and is off by default.
The operator story is about **operating communities and bots on someone else's infrastructure**,
and the trust story is: you trust Telegram with all default content everywhere.

### Family C: Federated / decentralised
*Matrix, XMPP, Session, SimpleX, Briar, Delta Chat, Nostr*

Many independently operated servers (or none at all) interoperate or relay. **The operator story
is the product here** — you can run the infrastructure, and in Matrix's case national governments
do. Costs shift to whoever runs servers; privacy adds a new edge case (federation exposes more
metadata to more parties, and every homeserver is its own legal and moderation jurisdiction).
The spectrum inside this family runs from "federated servers" (Matrix, XMPP) to "relays with no
user identifiers" (SimpleX) to "onion-routed swarms" (Session) to "no network at all" (Briar).

The trade that never goes away: **convenience requires someone to see more**. Sync, search,
discovery, notifications, group management, abuse reporting — each one is metadata or content
visibility that someone has to be trusted with, or an engineering trick that avoids it.

---

## 2. Threat-model taxonomy (the questions that decide everything)

### 2.0 First: "encrypted" is four different claims

Before the taxonomy below is any use, be precise about *which layer* is encrypted. Marketing
routinely conflates these four, and they are not degrees of the same thing:

| Claim | What it protects | Who can read content |
|---|---|---|
| **Transport encryption (TLS)** | the wire between client and server | the provider reads everything; protects against eavesdroppers on the network path only |
| **Encryption at rest** | stored data on disks | the provider holds the keys and can read content; protects against stolen physical disks only |
| **End-to-end encryption (E2EE)** | content across the entire path | only the endpoints — the provider cannot read content, but sees metadata |
| **E2EE with verified keys** | content **plus** identity assurance | only the endpoints, *and* you have verified the other party's key is theirs rather than one the server substituted |

> **⚠️ THE PRACTICAL TEST**
> **Can the provider show you your old messages on a new device with only a password? If yes, it is
> not end-to-end encrypted — or the backup isn't.** One question, and it cuts through every
> marketing claim. Telegram cloud chats fail it (→ `chat-telegram` §1.1); WhatsApp fails it unless
> E2EE backup is switched on; iMessage passes only with Advanced Data Protection; Signal passes,
> and its 2025 opt-in Secure Backups are zero-knowledge so it still passes (→ `chat-signal` §1.9).

And E2EE — even with verified keys — does not protect **metadata** (item 2 below), **the
endpoints** (a compromised phone defeats it completely; this is what commercial spyware buys),
**backups** (the most common real-world content leak), **the other party** (screenshot, forward, or
simply be untrustworthy), or **key distribution** where the provider supplies the public keys.

### 2.1 The seven axes

Before comparing apps, be precise about *private from whom, of what, against which attack*:

1. **Content privacy** — can the server read messages? (E2EE answers this; Telegram's default
   does not. Apple's taxonomy calls E2EE-without-PQ "Level 1" and grades up to "Level 3" for
   PQ-secured establishment *and* ongoing rekeying — see [Apple's PQ3 announcement, Feb 2024](https://security.apple.com/blog/imessage-pq3).)
2. **Metadata privacy** — can the server build the social graph? (Sealed Sender, zero-knowledge
   groups, identifier-free designs, onion routing all attack this. Nothing in mass deployment
   fully solves it.)
3. **Endpoint privacy** — is the phone the weakness? (Signalgate, forensic extraction, screen
   capture, iCloud-style backups, push-notification subpoenas. Most real-world failures are here.)
4. **Traffic privacy** — can the *network* observer see you use it? (Censorship resistance:
   TLS proxies, domain fronting, pluggable transports, or just being too popular to block.)
5. **Harvest-now-decrypt-later** — will today's ciphertext be readable in the cryptographically
   relevant quantum future? (The 2024–2026 post-quantum race — Signal, iMessage, SimpleX are in
   production; Threema in partnership; most others not started.)
6. **Compelled-access privacy** — how much does the operator even *have* when a subpoena or
   security order lands? (Signal's canonical answer: two timestamps. Telegram's post-2024 answer:
   considerably more. Sweden and the EU are currently legislating precisely this axis.)
7. **Organisational security** — can a staffer invite the wrong person to a classified group?
   (They can. E2EE does not fix identity confusion or admin error — the "Signalgate" lesson of
   March 2025.)

A useful rule: **apps solve 1–2 well, fight over 3–5, and get regulated over 6–7.**

> **⚠️ THE LEGAL ASYMMETRY IS WHY METADATA IS THE DESIGN DRIVER, NOT A NICE-TO-HAVE**
> Metadata alone yields relationships and their strength, sleep and work patterns, location history,
> health and legal circumstances (from who you called), religious and political affiliation, and the
> change points in a life — structured, machine-analysable at scale, and readable without reading
> anything. **In many jurisdictions it also receives markedly weaker legal protection than content,
> obtainable on a lower standard.** The most revealing category is the least protected. For
> high-risk users you reduce metadata because of legal process, not because of technical attacks —
> and the only defence that never fails is **not having the data**, which is why axis 6 above is the
> one that decides procurement (→ `chat-builder-and-operator-playbooks` §3 for the budget table).

---

## 3. Comparison matrix (state of play, September 2026)

| | Signal | Telegram | Matrix/Element | Wire | WhatsApp | iMessage | Session | SimpleX | XMPP+OMEMO | Briar | Delta Chat | Threema | Olvid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Architecture | A | B | C | A | A | A | C | C | C | C | C | A | A |
| Default 1:1 E2EE | ✅ | ❌ (opt-in only) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (mostly) | ✅ | ✅ | ✅ | ✅ |
| Default group E2EE | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Post-quantum (production) | ✅ Triple Ratchet ([Oct 2025](https://signal.org/blog/spqr/)) | ❌ | ❌ (MLS candidate for "Matrix 3.0") | Agility, PQ ciphersuite unverified | ❌ unverified | ✅ PQ3 ([2024](https://security.apple.com/blog/imessage-pq3/)) | Planned (Protocol v2) | ✅ hybrid sntrup761 ([v5.6, Mar 2024](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm/)) | ❌ | ❌ | ❌ | Research w/ IBM ([Feb 2026](https://threema.com/en/blog/quantum-secure-future)) | ❌ |
| Self-hostable | ❌ | ❌ | ✅ | ❌ (on-prem/edge variants for enterprise) | ❌ | ❌ | ✅ (service nodes, 25k SESH stake) | ✅ (relays) | ✅ | n/a (no servers) | ✅ (chatmail relays) | ❌ | ❌ |
| Phone number required | Yes (hidden by default since 2024 usernames) | Yes | No | Email/phone | Yes | Apple ID | No | No | No | No | Email | No | No |
| Open clients | ✅ | ✅ (server closed) | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (AGPL, reproducible) | ✅ |
| Scale | 70–100M MAU (Apr 2025, Whittaker via [SQ Magazine](https://sqmagazine.co.uk/signal-statistics/)) | ~1B MAU (Mar 2025) | ~19.5k federated servers ([TWIM Jul 2026](https://matrix.org/blog/2026/07/03/this-week-in-matrix-2026-07-03/)) | 1,800+ enterprise customers | ~3B MAU (2025) | ~1B+ devices | — (network of ~1.5–2k nodes) | 480k MAU ([Aug 2026](https://simplex.chat/blog/20260819-simplex-chat-crowdfunding.html)) | — | — | — | ~12M+ (est.) | 100k+ claimed |
| Funding model | Donations + new $1.99/mo backup tier | Ads + Premium + TON deals | Membership, donations, Element B2B | Enterprise SaaS | Meta business messaging | Device sales | Token staking + upcoming Pro | Donations + equity crowdfund | Donations/NLnet grants | Donations/grants | Donations/grants | Paid app + Work licences | B2B/B2G licences |
| Current crisis | Deficit; Sweden/EU legal threats | Durov prosecution; Russia squeeze | Foundation finances | — | Russia blocked it outright | — | Survived near-death 2026 | None known | Slow OMEMO 2 rollout | Maintenance mode | Healthy niche | New owner (Comitis, Jan 2026) | None known |

*Empty "scale" cells mean no trustworthy public figure — not zero.*

---

## 4. Timeline — how we got to the 2026 state of play

- **2013–2016** — Signal (TextSecure lineage) ships the protocol that everything since is measured
  against. Telegram launches cloud chats (2013). WhatsApp flips on Signal Protocol (2016).
- **2016–2019** — Wire begins the work that becomes **MLS**; Matrix reaches 1.0 of its spec;
  Signal ships Sealed Sender (2018); Session forks Signal onto the Oxen network (2020).
- **2021** — Academic paper: "Four Attacks and a Proof for Telegram" (Albrecht, Mareková,
  Paterson, Stepanovs; S&P 2022) — MTProto broken in theory, fixed in practice.
- **2023** — Signal ships **PQXDH** (post-quantum handshake); MLS becomes **RFC 9420**
  (March); Apple announces **PQ3** (shipped iOS 17.4, Feb 2024); Olvid gets French-government
  mandate (Nov 2023 circular); AWS kills consumer Wickr (31 Dec 2023).
- **2024** — Matrix 2.0 (Oct); Durov arrested in France (24 Aug); Signal usernames/phone-number
  privacy (Feb); Russia blocks Signal (Aug); SimpleX ships hybrid PQ ratchet (v5.6, Mar);
  Session migrates off Oxen (completes May 2025); Beeper/Texts go to Automattic (2023–24).
- **2025** — "Signalgate" (Mar) accelerates European sovereign-comms procurement; Wire ships MLS
  GA (24 Apr); WhatsApp DMA third-party interoperability goes live (Nov, with two small partners);
  Signal's **Triple Ratchet/SPQR** enters production rollout (2 Oct) and first paid feature ships
  (Secure Backups, 8 Sep); Russia restricts WhatsApp/Telegram calls (Aug) and pre-installs its own
  MAX messenger (1 Sep); Matrix.org Foundation warns "crossroads" and adds homeserver freemium.
- **2026 (to September)** — Russia fully blocks WhatsApp (Feb); Telegram slowdowns; Durov
  case drags on (4th questioning July; travel restrictions lifted Nov 2025); EU revives temporary
  "Chat Control" derogation (Reg. 2026/1881, in force 31 Jul 2026; E2EE exempt; permanent
  regulation still in trilogue); Threema acquired by Comitis Capital (Jan) and announces IBM
  Research PQ partnership (Feb); Briar enters maintenance mode (Jul); Session nearly dies, is
  community-rescued (Jun); Matrix nears its formal "2.0" spec cut; SimpleX launches equity
  crowdfunding (Aug).

---

## 5. The five forces reshaping private chat in 2026

1. **Post-quantum goes from blog posts to production.** Signal's Triple Ratchet and iMessage PQ3
   are deployed at population scale; everyone else is now behind. Expect "is it PQ?" to become a
   procurement checkbox (Wire and Threema are already selling to that checkbox).
2. **States are splitting the problem in two.** Russia is replacing foreign messengers with its
   own surveillance-friendly MAX app while blocking WhatsApp outright; liberal democracies fight
   over compelled scanning (EU Chat Control) and retention (Sweden). The direction of travel
   differs; the pressure on encryption is global.
3. **Sovereignty procurement.** NATO NI2CE, France's Tchap/La Suite, Germany's
   BundesMessenger/openDesk, UNICC — governments are insourcing secure comms to self-hosted Matrix.
   This is Matrix's business model now.
4. **Forced interoperability is real but shallow.** DMA Article 7 produced exactly two interoperable
   WhatsApp partners so far; IETF MIMI is still pre-RFC. Watch whether big players ever connect.
5. **The economics are unforgiving.** Signal spends ~$38M/yr and ran a deficit; Matrix.org is
   reducing losses but lean; Session nearly died; Briar is in maintenance mode; Telegram profits
   only by being a platform + crypto economics. "Free, private, and sustainable" can pick two.

*(All dated claims above are sourced inside `chat-signal`, `chat-telegram`, `chat-matrix-and-element` and `chat-the-wider-field`; the Sources section at the end of each
file carries publisher, date and what was actually said.)*
