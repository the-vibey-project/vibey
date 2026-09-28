---
id: skill-11-the-attack-literature-what-actually-threatens-tor-users-82a1ccb752
purpose: 11 the attack literature what actually threatens tor users
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-attack-literature-and-threat-model/SKILL.md
requires: []
links: ["skill-where-to-go-next-1e618529c2"]
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
