---
id: skill-1-what-tor-is-what-it-promises-and-what-it-does-not-5471d94b00
purpose: 1 what tor is what it promises and what it does not
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-protocol-circuits-and-cell-cryptography/SKILL.md
requires: []
links: ["skill-2-history-and-lineage-c8a8e66c92"]
---

## §1. What Tor is, what it promises, and what it does not

Tor is a low-latency anonymity overlay network: roughly 9,200 volunteer relays and 2,300
bridges carrying traffic for several million daily users (network-size and user CSV data
from [Tor Metrics](https://metrics.torproject.org/), 8–14 Sept 2026; see §6 →
`tor-network-consensus-guards-and-paths` for detail). A client's traffic is routed through a
chain ("circuit") of three independently operated relays, with layered ("onion") encryption
such that:

- the **first relay (guard)** knows *who you are* but not what you're doing;
- the **middle relay** knows neither;
- the **exit relay** (or onion-service rendezvous point) knows *what is being done* but not
  *by whom*.

The design goal is **unlinkability**: no single entity — relay, ISP, destination server —
should be able to connect a user's identity to their activity. Tor provides *transport-layer*
anonymity: it hides network endpoints, not the content or the behavior inside the stream.

### ⚠️ What Tor deliberately does not promise

Per its own threat model:

- **Protection against a global passive adversary.** Anyone who can watch both ends of a
  circuit (e.g., your ISP *and* the destination's network) can confirm relationships by
  timing/volume correlation. Tor is low-latency by design; defeating end-to-end correlation
  is what high-latency mix networks try to do instead (§14 →
  `tor-ecosystem-alternatives-and-governance`).
- **Confidentiality past the exit relay.** Exit traffic to a clearnet site leaves the Tor
  envelope. Use end-to-end encryption (HTTPS) as usual; Tor Browser bundles HTTPS-only mode
  partly for this reason.
- **Application-level anonymity.** Logging into your personal account over Tor, or running a
  browser that leaks identifying fingerprints, defeats the network layer. This is why the Tor
  Project ships a hardened browser rather than telling people to point any app at a SOCKS
  proxy.
- **Invisibility.** A censor can see that you *are using* Tor unless you use a pluggable
  transport (§10 → `tor-censorship-circumvention-and-bridges`). Tor hides destinations, not
  the fact of its use.

A useful mental model: Tor gives you **three organizational trust boundaries** per circuit
plus layered crypto, and then throws engineering effort (guards, congestion control, padding
research, anti-enumeration transports) at shrinking the residual deanonymization surface.

---
