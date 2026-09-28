---
id: skill-6-the-network-itself-relays-authorities-consensus-weights-444e9d6cf9
purpose: 6 the network itself relays authorities consensus weights
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-network-consensus-guards-and-paths/SKILL.md
requires: []
links: ["skill-7-guard-selection-and-path-restrictions-588016dc49"]
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
