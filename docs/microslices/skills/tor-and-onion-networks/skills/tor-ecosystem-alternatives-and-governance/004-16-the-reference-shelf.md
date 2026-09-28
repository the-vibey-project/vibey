---
id: skill-16-the-reference-shelf-4ee5cf37c1
purpose: 16 the reference shelf
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-ecosystem-alternatives-and-governance/SKILL.md
requires: ["skill-15-governance-funding-and-the-human-network-9585c31b09"]
links: ["skill-where-to-go-next-acddf0085c"]
---

## §16. The reference shelf

### §16.1 Specifications (start here)

- [Tor Specifications index](https://spec.torproject.org/) — `tor-spec` (cells/circuits),
  `rend-spec-v3` (onion services), `dir-spec` (directory protocol), `control-spec` (controller
  API), `socks-extensions`, `vanguards-spec`, `pt-spec`.
- [Proposals index](https://spec.torproject.org/proposals/) — every design change. Greatest
  hits: 224/225 (v3 services), 236 (single-guard-era path), 271 (guard sets), 292 (mesh
  vanguards), 308 & **359** (CGO), 321 (happy families), 324 (congestion control), 327 (PoW),
  329 (Conflux), 332/346 (ntor-v3 & subprotocol negotiation).
- RFC 7686 — `.onion` special-use domain name.

### §16.2 Foundational and attack papers

- Dingledine, Mathewson, Syverson — *Tor: The Second-Generation Onion Router*, USENIX Security
  2004.
- Goldberg, Stebila, Ustaoglu — *Anonymity and One-Way Authentication in Key-Exchange
  Protocols* (the ntor design), 2013.
- Johnson et al. — *Users Get Routed: Traffic Correlation on Tor by Realistic Adversaries*,
  CCS 2013.
- Biryukov, Pustogarov, Weinmann — *Trawling for Tor Hidden Services*, IEEE S&P 2013.
- Øverlier & Syverson — *Locating Hidden Servers*, IEEE S&P 2006.
- Murdoch & Danezis — *Low-Cost Traffic Analysis of Tor*, S&P 2005.
- Winter et al. — *Spoiled Onions: Exposing Malicious Tor Exit Relays*, PETS 2014.
- Panchenko et al. — *Website Fingerprinting in Onion Routing…* (kNN), WPES 2016.
- Rimmer et al. — *Automated Website Fingerprinting through Deep Learning*, CCS 2018.
- Wang & Goldberg — *Walkie-Talkie* (USENIX Sec 2017); Juarez et al. — *WTF-PAD* (2016).
- Rochet & Pereira — *Waterfilling* / *Dropping on the Edge*, PETS 2018.
- Degabriele, Melloni, Münch, Stam — the CGO design papers behind proposals 308/359.

### §16.3 Living status pages (check these rather than trusting this document's dates)

- [Tor Project blog](https://blog.torproject.org/) — release announcements (Arti, C tor, Tor
  Browser, Tails).
- [Tor Metrics](https://metrics.torproject.org/) — live network data + CSV export.
- [Onion Services Ecosystem docs](https://onionservices.torproject.org/) — authoritative
  service-operator documentation (PoW FAQ, DoS guidelines, Onionbalance, Onionspray).
- [Community portal](https://community.torproject.org/) — relay/bridge operator guides.
- [net4people/bbs](https://github.com/net4people/bbs) — the censorship-research forum where
  blocking events (e.g. the 2026 Snowflake fingerprinting campaign) are dissected in real
  time.
- [Tor Project forum](https://forum.torproject.org/) — operator support, Snowflake daily-ops
  reports.

---
