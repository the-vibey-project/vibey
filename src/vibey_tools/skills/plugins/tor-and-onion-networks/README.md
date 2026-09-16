# Tor and Onion Networks Plugin

The Tor network in three parts: the protocol, the operated system, and what it takes to build
on it. Cells, channels and the telescoping circuit handshake, the ntor family and the tor1 →
CGO cell-cryptography migration, SENDME flow control and the congestion-control and Conflux
work that followed; then the network as an operated thing — relays and flags, the nine
directory authorities, the hourly consensus, bandwidth weights, guard pinning and path
restrictions; then v3 onion services end to end with the hardening stack around them
(vanguards, proof-of-work, Onionbalance), the censorship arms race of bridges and pluggable
transports, the attack literature ordered by what actually deanonymizes people, the 2026
software ecosystem and the alternatives, and an operations handbook of configuration and code.

One reference, split into 8 skills along its section groups so a task loads only the part it
needs. Section numbers (§N) are shared across the set and cross-references into a sibling skill
are written as §N → `skill`. Reference, not tutorial: sections are independent, every claim is
tagged by how durable it is (stable protocol fundamentals vs. versioned specifics vs. genuinely
fast-moving censorship status), and a currency snapshot (compiled September 2026) flags what
goes stale first — §10 above all.

Nothing here routes around the law. Relays, bridges and onion services are legal in most
jurisdictions and abused in the same way roads are; the operations skill carries the abuse,
notice and exit-operator obligations alongside the configuration.

## Skills

- **tor-protocol-circuits-and-cell-cryptography** — What Tor Is and Is Not, History, the Core
  Protocol, Circuit Cryptography, and Flow Control (§1–§5): ⚠️ What Tor deliberately does not
  promise; History and lineage; Cells, circuits and the telescoping handshake; ⚠️ Where the TLS
  ends; TAP → ntor → ntor-v3; ⚠️ tor1 and its CGO replacement; SENDME, congestion control and
  Conflux.
- **tor-network-consensus-guards-and-paths** — The Network Itself and Path Selection (§6–§7):
  Relays and flags; ⚠️ The nine directory authorities and the consensus; Bandwidth weights;
  Users and how they are counted; Reading the network with Relay Search, Onionoo, ExoneraTor
  and CollecTor; ⚠️ Why guards exist; Path-selection restrictions; ⚠️ Happy families.
- **tor-onion-services-and-hardening** — Onion Services v3 and Hardening Them (§8–§9): ⚠️ The
  address is the key; Publishing a service and blinded descriptors; Connecting via introduction
  and rendezvous points; ⚠️ What changed from v2; ⚠️ Guard discovery and vanguards; Proof-of-work
  DoS defense; Onionbalance, Onionspray and EOTK; Onion-Location and Alt-Svc discovery.
- **tor-censorship-circumvention-and-bridges** — Bridges and Pluggable Transports (§10):
  ⚠️ Fingerprinting vs. enumeration; obfs4, Snowflake, WebTunnel, meek and Conjure; Bridge
  distribution channels; ⚠️ The 2026 Snowflake DTLS war; Iran's 2025 stealth blackout.
- **tor-attack-literature-and-threat-model** — What Actually Threatens Tor Users (§11): ⚠️
  End-to-end confirmation as a design limit; ⚠️ Website fingerprinting and why no defense
  ships by default; Guard discovery; Sybil and malicious-relay campaigns; Exit content
  attacks; HSDir harvesting; Denial of service; ⚠️ Client-side deanonymization.
- **tor-ecosystem-alternatives-and-governance** — The 2026 Ecosystem, the Alternatives, and the
  Reference Shelf (§12, §14–§16): ⚠️ C tor vs. Arti; End-user platforms; Operator and developer
  tooling; ⚠️ Tor against I2P, mixnets and VPNs; Governance and funding; Specs, proposals and
  the foundational papers.
- **tor-building-on-tor-software-patterns** — Building on Tor in Code (§13.1–§13.4, handbook
  §1): The five patterns; ⚠️ `socks5h` and stream isolation; The control port and ephemeral
  onion services; Long-lived onion services in torrc and client authorization v3;
  Onion-Location and Alt-Svc; ⚠️ torsocks and its honest limits; Embedding Arti; Testing
  against chutney.
- **tor-running-relays-bridges-and-hardware** — Running Infrastructure (§13.5, handbook §2–§6):
  Middle and guard relays; ⚠️ obfs4 and WebTunnel bridges and Snowflake proxies; ⚠️ Exit relays
  and their prerequisites; Transparent-proxy gateways and DNS-leak prevention; Raspberry Pi,
  travel-router and two-box builds; The SecureDrop architecture; Verification checklist;
  ⚠️ Legal, ethical and abuse handling.

## Provenance

Derived from two compiled references — a deep dive covering §1–§16 and an operations handbook
covering the configuration and code — both compiled 16 September 2026. The skills here carry
that material in full, reorganized so a task loads only the part it needs; the source documents
are deliberately not committed under `docs/`, which is the nav-driven input to vibey's own
published book and research paper.
