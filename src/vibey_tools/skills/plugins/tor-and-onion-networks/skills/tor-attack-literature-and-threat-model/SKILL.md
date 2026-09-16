---
name: tor-attack-literature-and-threat-model
description: "Use when assessing what actually threatens Tor users, or when checking a deanonymization claim against the literature — end-to-end confirmation, website fingerprinting and why no defense ships by default, guard discovery, Sybil and malicious-relay campaigns (KAX17, the 2020 exit wave), exit content attacks, HSDir harvesting, DoS, and client-side compromise. Covers §11. Companion to the other Tor and onion-network skills."
---

# What Actually Threatens Tor Users

> **Part 5 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §11. Sibling skills:
> `tor-protocol-circuits-and-cell-cryptography` (§1–§5),
> `tor-network-consensus-guards-and-paths` (§6–§7),
> `tor-onion-services-and-hardening` (§8–§9),
> `tor-censorship-circumvention-and-bridges` (§10),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-building-on-tor-software-patterns` (§13.1–§13.4, handbook §1),
> `tor-running-relays-bridges-and-hardware` (§13.5, handbook §2–§6).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **Currency:** compiled 16 September 2026. The attack *taxonomy* is durable — these
> categories have been stable for a decade. **Specific accuracy figures, campaign details and
> CVE numbers are dated.** Full citations in §16 →
> `tor-ecosystem-alternatives-and-governance`.

> **⚠️ Ordered by practical significance, not by how interesting the mathematics is. The
> category that deanonymizes the most real people is the last one, and it is not a protocol
> attack.**
>
> **⚠️ GOTCHA** boxes mark where the mental model people carry is wrong — including where
> the *security* literature is routinely over-claimed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ END-TO-END CONFIRMATION IS A DESIGN LIMIT, NOT A BUG** (§11.1). **Tor is
>    low-latency by choice. Anyone watching both ends can correlate. Every deployed defense
>    raises the required vantage point; none removes the property. Claims that Tor "defeats"
>    a global adversary are wrong at the design level.**
> 2. **⚠️ NO GENERAL WEBSITE-FINGERPRINTING DEFENSE SHIPS BY DEFAULT** (§11.2). **The
>    circuit-padding *framework* is merged. The defenses built on it are not on. Treat any
>    claim that "Tor defends against WF" as false unless it names a specific enabled
>    machine.**
> 3. **⚠️ THE BIGGEST REAL-WORLD CATEGORY IS CLIENT-SIDE** (§11.8). **Browser exploits,
>    logins, document metadata and plugin leaks deanonymize far more people than traffic
>    analysis. This is why the answer is Tor Browser, Tails and Whonix rather than "point any
>    app at a SOCKS proxy".**

---

## §11. The attack literature: what actually threatens Tor users

Ordered by practical significance. Cited papers are in §16 →
`tor-ecosystem-alternatives-and-governance`.

### §11.1 End-to-end traffic confirmation

The root limitation. Guard pinning helps; distance helps; padding helps marginally. No
deployed defense defeats a genuinely global observer — the response is to raise the
adversary's required vantage (guards, family/AS diversity research like Waterfilling) rather
than to claim impossibility.

### §11.2 Website fingerprinting (WF)

A guard-side observer (or ISP) classifies *which site* a circuit visits from packet
sizes/directions/timing alone — kNN (Panchenko), CUMUL, then **Deep Fingerprinting** (Rimmer
et al., CCS 2018) showed CNNs hitting ~95%+ accuracy undefended.

Defenses (WTF-PAD, Walkie-Talkie, Tamaraw) exist in the literature and Tor's **circuit padding
framework** (a state-machine mechanism for negotiated padding) is merged in the client.

> **⚠️ GOTCHA:** as of 2026 **no general WF defense is on by default** — cost/latency
> tradeoffs remain unresolved. Treat "WF defenses are deployed" claims skeptically, and note
> that published accuracy figures are usually closed-world laboratory numbers that degrade
> substantially in open-world conditions.

### §11.3 Guard discovery against onion services

See §9.1 → `tor-onion-services-and-hardening`; mitigated by vanguards (Arti) and shortened
circuit lifetimes.

### §11.4 Sybil / malicious-relay campaigns

Real and recurring: the 2020 malicious-exit wave (SSL-stripping; at one point ~23% of exit
capacity before eviction), the long-running **KAX17** actor (2021 disclosure; hundreds of
relays across entry/middle/exit).

Countermeasures: authority-side eviction heuristics, family verification (happy families,
§7.3 → `tor-network-consensus-guards-and-paths`), bandwidth-authority measurement making
low-capacity Sybils cheap to suspect, and community relay-health monitoring.

### §11.5 Exit-relay content attacks

Spoofing/poisoning past the exit (the 2014 *Spoiled Onions* study cataloged HTTPS/SSH MITM,
DNS poisoning, and binary injection attempts). The defense is boring and effective: end-to-end
crypto to the destination, HTTPS-only mode, and checking exits via `BadExit` reporting
pipelines.

### §11.6 HSDir descriptor harvesting

v3's blinded keys largely closed the v2-era enumeration hole (§8.4 →
`tor-onion-services-and-hardening`); operators should still assume *addresses are discoverable
if leaked elsewhere* — in a referrer header, a certificate transparency log, a screenshot, or
a search index.

### §11.7 Denial of service

The 2022–2023 intro-flooding campaigns against prominent services motivated PoW (§9.2 →
`tor-onion-services-and-hardening`) and memory-quota hardening; Conflux queue and
circuit-extension DoS CVEs (e.g., CVE-2026-44600) keep landing. Defensive posture: current
tor, PoW, rate limits, Onionbalance.

### §11.8 ⚠️ Client-side deanonymization

The biggest *practical* category: browser exploits (drive-by against Tor Browser users
historically), plugins, document metadata, login reuse, clock skew.

None of these are protocol attacks — they're why Tails/Whonix and Tor Browser's security
levels (Standard/Safer/Safest, with NoScript-managed JS/Wasm) exist. A threat model that
spends all its attention on traffic analysis and none on the browser has the priorities
inverted relative to the historical record.

---

## Where to go next

- Why guards exist at all, and the *Users Get Routed* result behind §11.1: §7.1 →
  `tor-network-consensus-guards-and-paths`.
- Vanguards and PoW, the deployed answers to §11.3 and §11.7: §9 →
  `tor-onion-services-and-hardening`.
- Tails, Whonix and Tor Browser security levels — the answer to §11.8: §12.2 →
  `tor-ecosystem-alternatives-and-governance`.
- Full paper citations: §16.2 → `tor-ecosystem-alternatives-and-governance`.
