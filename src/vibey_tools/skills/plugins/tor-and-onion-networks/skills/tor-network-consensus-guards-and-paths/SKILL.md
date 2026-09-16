---
name: tor-network-consensus-guards-and-paths
description: "Use when reasoning about the Tor network as an operated system — relays and flags, the nine directory authorities, the hourly consensus, bandwidth weights, guard pinning and why it exists, path-selection restrictions, and happy families — or when looking up a relay with Relay Search, Onionoo, ExoneraTor or CollecTor. Covers §6–§7. Companion to the other Tor and onion-network skills."
---

# The Tor Network: Relays, Authorities, Consensus, and Path Selection

> **Part 2 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §6–§7. Sibling skills:
> `tor-protocol-circuits-and-cell-cryptography` (§1–§5),
> `tor-onion-services-and-hardening` (§8–§9),
> `tor-censorship-circumvention-and-bridges` (§10),
> `tor-attack-literature-and-threat-model` (§11),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-building-on-tor-software-patterns` (§13.1–§13.4, handbook §1),
> `tor-running-relays-bridges-and-hardware` (§13.5, handbook §2–§6).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **Currency:** compiled 16 September 2026. Guard logic and consensus mechanics are stable.
> **Relay counts, user counts and version-gated features are dated** — pull live figures from
> [Tor Metrics](https://metrics.torproject.org/) rather than quoting this document.

> **⚠️ Tor's trust root is nine servers run by nine named people. Everything else is
> volunteers.**
>
> **⚠️ GOTCHA** boxes mark where the mental model people carry is wrong in ways that cause
> real deanonymization or bad operational decisions.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE CONSENSUS IS THE NETWORK** (§6.2). **There is no peer-to-peer discovery. Nine
>    directory authorities vote hourly on who exists and how much they weigh, and clients
>    trust that signed document. Majority compromise is the nightmare scenario, which is why
>    authority diversity is a governance question, not an engineering one.**
> 2. **⚠️ GUARDS TRADE A CERTAINTY FOR A RARITY** (§7.1). **Rotating first hops randomly
>    means an adversary with a modest relay fraction *eventually* becomes your entry. Pinning
>    a small guard set for months converts "eventually certain" into "probably never" — and
>    is why New Identity deliberately does not change your guard.**
> 3. **⚠️ PATH RESTRICTIONS ARE ANTI-CORRELATION, NOT PRIVACY CONTROLS** (§7.2). **Family
>    and /16 rules exist so one operator cannot own two hops. `ExitNodes` country pinning is
>    advisory routing preference, not a safety property — the exit still sees your traffic.**

---

## §6. The network itself: relays, authorities, consensus, weights

### §6.1 Actors

- **Relays** (~9,200 running in mid-September 2026; Tor Metrics `networksize.csv`: 10,065 on
  20 Aug 2026 declining to 9,228 by 14 Sept — treat single weeks as noisy): volunteer-operated
  nodes. Flags matter: `Guard` (stable, fast, trustworthy enough to be first hops), `Exit`
  (allowed final hops), `HSDir` (hold onion-service descriptors), `Fast`, `Stable`, `Running`,
  `Valid`, `BadExit`.
- **Directory authorities (9).** The trusted core: nine long-lived servers run by different
  known individuals/organizations (moria1, tor26, dizum, gabelmoo, dannenberg, maatuska,
  Faravahar, longclaw, bastet). Every hour they vote on the set of relays and compute a
  **consensus** — the signed, authoritative network document. Five-of-nine agreement is what
  keeps the network self-consistent; compromise of the majority is the nightmare scenario, and
  it's why authority diversity and physical security are taken so seriously.
- **Fallback directory mirrors** (~100+ hard-coded relays) so new clients can fetch a
  consensus even if they've never heard of an authority.
- **Bandwidth authorities.** A subset of authorities additionally run **sbws** scanners that
  actively measure relay throughput; their votes set consensus weights so clients pick relays
  in proportion to real capacity.
- **Bridges** (~2,300 in Sept 2026): unlisted guard-like entry nodes for censored users,
  distributed out-of-band (§10 → `tor-censorship-circumvention-and-bridges`).

### §6.2 Consensus mechanics

Hourly cycle: authorities publish *votes* (~:50 past the hour), exchange them, and produce a
*consensus* valid for three hours. Clients and relays download **microdescriptors** (compact
relay records keyed by digest) rather than full descriptors — this is what made Tor usable on
mobile links. Consensus *methods* version the format itself; 0.4.9 dropped support for
consensus methods older than 32. A **consensus transparency** experiment (signed-tree logging,
CT-style, to detect split-view attacks against directory clients) was underway as of the 0.4.9
series, with unsigned-consensus export support added for it.

### §6.3 Users

Tor Metrics estimates (from directory-request extrapolation, requests/10 per client per day —
see their [reproducible metrics
methodology](https://metrics.torproject.org/reproducible-metrics.html)): **~2.8–3.5 million
directly-connecting users per day in September 2026**, plus bridge users counted separately.
Largest populations (Sept 2026 top-10 table): US (~515k, ~15.5%), Germany (~294k), Brazil,
Finland, India, France. Usage spikes historically track censorship events and conflicts (Iran
June 2025 being the sharpest recent example — §10.4 →
`tor-censorship-circumvention-and-bridges`).

> **⚠️ GOTCHA:** "Tor user counts" are *estimates derived from directory requests*, not
> logins. They are extrapolations with a documented methodology and known error bars. Never
> present them as a census, and never compare across a methodology change without reading the
> metrics notes.

### §6.4 Reading the network yourself

- [Relay Search](https://metrics.torproject.org/rs.html) — per-relay detail: flags, weights,
  family, history.
- **Onionoo** — the REST/JSON API behind Relay Search and most third-party tooling.
- **CollecTor** — descriptor archives for research.
- **ExoneraTor** — "was IP X a Tor exit on date Y?" (the answer to most "was it Tor?" abuse
  questions).
- **Exit list / DNSBL** — live exit enumeration for destination-side filtering design.

---

## §7. Guard selection and path restrictions

### §7.1 Why guards exist

The 2013 paper *Users Get Routed* (Johnson et al., CCS 2013) quantified what everyone feared:
if clients rotate first hops randomly, an adversary running a modest fraction of relays
*eventually* becomes the first hop and can run confirmation attacks. The fix — pin a small set
of first hops for **months** — turned a probabilistic certainty into a probabilistic rarity.

Modern rules (proposal 271 and successors): a **sampled guard set**, filtered for
reachability, of which the client uses 2–3 **primary guards**, rotating only on failure or
expiry.

> **⚠️ GOTCHA:** "Get a new identity often" is **not** the same as changing guards, and Tor
> Browser's New Identity keeps your guards *deliberately*. Advice that tells users to churn
> entry nodes for safety inverts the actual security argument — churn is what guards exist to
> prevent.

### §7.2 Path selection restrictions

Circuits are built subject to constraints that any builder must replicate:

- relays in one circuit must not share a **family** or (by default) a **/16**;
- exit policies must permit the destination port;
- consensus weights bias selection toward capacity (and `Guard`/`Exit` fractional weights keep
  exit-scarce bandwidth available for exit use);
- country restrictions only via explicit torrc (`ExitNodes`, `ExcludeNodes`, `GeoIP...`) — and
  these are advisory for privacy, not robust safety properties, since the exit or a router
  downstream sees your traffic anyway.

### §7.3 Happy families (proposal 321; shipped in C tor 0.4.9, 2026)

`MyFamily` mutual cross-listing was error-prone and bloated descriptors (O(family²)
fingerprints). 0.4.9 adds a shared **family key**: relays sign a certificate proving family
membership, collapsing family proof to a single identifier. Tor Project estimates eventual
**~80% microdescriptor size reduction**.

> **⚠️ GOTCHA for relay operators:** until client adoption catches up, you must maintain
> `MyFamily` **in parallel** with the new family key. Dropping `MyFamily` early makes your
> relays look unrelated to older clients, which is exactly the correlation risk families exist
> to prevent. See the [family-ids
> documentation](https://community.torproject.org/relay/setup/post-install/family-ids/).

---

## Where to go next

- How cells and circuits actually work underneath all of this: §3 →
  `tor-protocol-circuits-and-cell-cryptography`.
- Why onion services need *extra* guard layers on top of this: §9.1 →
  `tor-onion-services-and-hardening`.
- Sybil campaigns and malicious relays against this trust model: §11.4 →
  `tor-attack-literature-and-threat-model`.
- Running a relay, bridge or exit yourself: §13.5 → `tor-running-relays-bridges-and-hardware`.
