---
name: tor-onion-services-and-hardening
description: "Use when working with v3 onion services — the 56-character address format, blinded descriptor keys, introduction and rendezvous points, client authorization, single-onion mode — or when hardening one with vanguards, proof-of-work DoS defense, Onionbalance and Onionspray, or advertising it via Onion-Location. Covers §8–§9. Companion to the other Tor and onion-network skills."
---

# Onion Services v3: How They Work, and How to Keep Them Standing

> **Part 3 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §8–§9. Sibling skills:
> `tor-protocol-circuits-and-cell-cryptography` (§1–§5),
> `tor-network-consensus-guards-and-paths` (§6–§7),
> `tor-censorship-circumvention-and-bridges` (§10),
> `tor-attack-literature-and-threat-model` (§11),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-building-on-tor-software-patterns` (§13.1–§13.4, handbook §1),
> `tor-running-relays-bridges-and-hardware` (§13.5, handbook §2–§6).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **Currency:** compiled 16 September 2026. The v3 protocol is stable. **Tooling status in
> §9 moves fast** — the vanguards addon is unmaintained, PoW/Onionbalance compatibility is a
> live constraint, and the C tor → Arti transition changes the recommended stack. Verify
> against <https://onionservices.torproject.org/>.

> **⚠️ Onion services invert the trust direction: the *server* becomes location-anonymous,
> and the connection never leaves the network.**
>
> **⚠️ GOTCHA** boxes mark where the mental model people carry is wrong in ways that get
> services deanonymized or knocked offline.
>
> **The three ideas that organize this document:**
> 1. **⚠️ THE ADDRESS *IS* THE PUBLIC KEY** (§8.1). **A `.onion` is
>    `base32(ed25519_pubkey ‖ checksum ‖ version)`. No CA, no DNS, no trust-on-first-use —
>    the name authenticates the service by construction, which is why TLS is not needed for
>    authentication *to* the service.**
> 2. **⚠️ LONG-LIVED CIRCUITS ARE THE ATTACK SURFACE** (§9.1). **A service keeps intro and
>    rendezvous circuits up for a long time, and an adversary who can force it to rebuild
>    them repeatedly walks up the path toward its guard. Vanguards exist because the standard
>    three-hop assumption is not enough when the server is the thing being hidden.**
> 3. **⚠️ HARDENING FEATURES CONFLICT WITH EACH OTHER** (§9.2, §9.3). **PoW does not work
>    with Onionbalance. The vanguards addon does not work with Conflux. There is no
>    configuration that turns everything on — you pick per threat model.**

---

## §8. Onion services (v3) end to end

Onion services flip the trust direction: the *server* becomes location-anonymous, and the
connection never leaves the network. (The client stays anonymous too — onion services are
mutually anonymous.)

### §8.1 The address is the key

A v3 address is **56 base32 characters** = `base32(ED25519_PUBKEY ‖ CHECKSUM ‖ VERSION)` where
`CHECKSUM = SHA3-256(".onion checksum" ‖ PUBKEY ‖ VERSION)[0:2]` and VERSION = 0x03.

Consequences:

- addresses are **self-authenticating** (no CA, no DNS);
- **un-phishable by near-match** — 35 bytes of entropy means a vanity prefix is a GPU
  birthday search (see `mkp224o`), and a full-address collision is infeasible;
- **TLS is unnecessary for authentication to the service** — though HTTPS-over-onion
  certificates exist; DigiCert has issued EV certs for `.onion` under CA/Browser Forum rules
  since Facebook's 2015 deployment.

### §8.2 Publishing a service

1. **Generate keys.** The service's ed25519 master identity can be kept **offline**
   (`tor --keygen`); day-to-day operation uses a medium-term signing key — compromise of the
   running box doesn't permanently compromise the address.
2. **Pick introduction points.** The service builds 3-hop circuits to (by default) 3 relays it
   selects, which become its intro points; it hands each an intro-point auth key.
3. **Compute blinded keys.** For each ~24h period, the descriptor-signing key is *blinded*
   with a period-derived nonce, so neither HSDirs nor clients can link yesterday's descriptor
   to today's without the master public key.
4. **Upload descriptors** to the six HSDirs chosen by blinded-key position in the directory
   ring (two replicas, three consecutive HSDirs each), where they sit with a ~3-hour lifetime;
   **revision counters** are encrypted with an order-preserving construction so HSDirs can
   pick the newest descriptor without learning service churn.

### §8.3 Connecting (client side)

1. Client derives today's blinded key from the `.onion` public key, fetches the descriptor
   from the right HSDirs (3-hop circuits; the HSDir learns only that *someone* is fetching
   *somewhere*, not whom).
2. Client picks a random **rendezvous point** relay, connects (3 hops), and hands it a
   one-time rendezvous cookie.
3. Client encrypts (hs-ntor) an intro message to one intro point: rendezvous cookie + RP
   identity.
4. The service (optionally after **client authorization** checks — v3 uses per-client x25519
   keys: `.auth_private` on the client, `authorized_clients/` on the server) builds a 3-hop
   circuit to the RP and completes the handshake.
5. Result: a **6-hop** end-to-end circuit — client-guard…RP…service-guard — with both sides
   anonymous to each other and both using their own pinned guards.

`SingleOnionService` mode (server opens directly to the RP, 3 hops total) trades server
anonymity for ~half the latency — popular for services that only need encryption and
NAT-bypass, e.g., SecureDrop-style upload boxes behind hostile networks.

### §8.4 ⚠️ GOTCHA: what changed from v2, and why it matters to builders

v2 services (RSA-1024, SHA-1-derived 16-char names, descriptor replay weaknesses, HSDir
enumeration via predictable indices — the *Trawling for Tor Hidden Services* attack,
Biryukov/Pustogarov/Weinmann 2013) were **removed from the network in October 2021**.

Any tutorial, library, or product speaking v2 is **dead code**. If a guide mentions
`HidServAuth`, 16-character addresses, or `rend-spec-v2`, it predates the cutoff and every
security claim in it should be re-checked from scratch.

---

## §9. Hardening onion services: vanguards, proof-of-work, load balancing

### §9.1 Guard-discovery attacks and vanguards

Onion services keep their intro-point and rendezvous circuits up for long periods. An
adversary who can *force* a service to build many circuits (e.g., by knocking on its intro
points) can, over days-to-weeks, enumerate middle hops and eventually land as the service's
guard — at which point guard-side traffic confirmation identifies the server's location. This
is the attack family (Øverlier & Syverson 2006 onward) behind several real-world service
deanonymizations.

**Vanguards** (proposal 292 → the standalone [vanguards
spec](https://spec.torproject.org/vanguards-spec/)) fixes this by pinning *additional* fixed
guard layers under the service:

- **Vanguards-Lite** (default): one extra pinned layer (L2: 4 relays, lifetimes in days) —
  cheap, big win.
- **Full Vanguards**: L2 + L3 pinned layers with short L3 rotation (hours) and an extra hop —
  for long-lived, high-value services.

> **⚠️ GOTCHA — status as of Feb–Sept 2026:** the original C-tor Python addon is
> **unmaintained** (no commits since Oct 2023), **incompatible with Conflux**, was pulled from
> Debian Trixie, and is disabled in Whonix 18. **Native vanguards ship in Arti** (since 1.2.2,
> default-on; security-refined by 1.2.5). For production services in 2026 this is a live
> decision point: C tor 0.4.9 + PoW, or Arti (service support declared production-useable with
> the disclaimer removed in Arti 1.8.0, Dec 2025) + vanguards. The spec intends Vanguards-Lite
> as the universal default once Arti replaces C tor.

### §9.2 Proof-of-work DoS defense (proposal 327; shipped tor 0.4.8, Aug 2023)

Intro-point flooding was the dominant onion-service DoS vector. The PoW defense adds a
*reactive, adaptive* puzzle (Equi-X proof + HashX verification):

- Dormant in normal operation; under load the service raises "suggested effort" in the
  descriptor/intro protocol.
- Legit clients burn tens of milliseconds to seconds of CPU per intro attempt; a botnet must
  multiply that cost by its request rate — cheap for humans, expensive at attack scale.
- Configured via `HiddenServicePoWDefensesEnabled 1` (+ `QueueRate`/`QueueBurst`), built with
  `--enable-gpl` (Equi-X/HashX licensing), monitored via MetricsPort `tor_hs_pow_*` metrics.

> **⚠️ GOTCHA:** PoW is a **priority queue, not a wall**. Very large botnets still overwhelm;
> mobile clients suffer at high difficulties; and — the constraint that bites real
> deployments — **PoW is incompatible with Onionbalance** as of 2025–2026 documentation. PoW
> also landed in Arti experimentally in 2026.

### §9.3 Scaling: Onionbalance, Onionspray, EOTK

- **[Onionbalance](https://onionservices.torproject.org/apps/base/onionbalance/)** (v0.2.4,
  Apr 2025; actively maintained, v2 code removed in 0.2.3): a master node aggregates intro
  points from N backend tor instances (up to ~60 distinct intro points) into one published
  descriptor — horizontal scaling and failover for one address. JSON **status socket** for
  monitoring.
- **[Onionspray](https://onionservices.torproject.org/apps/web/onionspray/)**: the Tor
  Project's modern answer to Alec Muffett's EOTK — config-driven generation of whole onion
  sites (hardmap = direct backends; softmap = Onionbalance-mediated), including multi-server
  topologies and publisher/backend key isolation.
- **EOTK** itself: historically important (BBC, NYT, Brave deployments), effectively
  superseded by Onionspray for new builds.

### §9.4 Discovery: how humans find onion sites

- **`Onion-Location` HTTP header** (Tor Browser ≥ 9.5): serve
  `Onion-Location: http://<addr>.onion$request_uri` over HTTPS from your clearnet site; Tor
  users get a purple ".onion available" pill / optional always-redirect. Works in
  nginx/Apache/Caddy or as a meta tag.
- **`Alt-Svc: ... ; ma=...` to the onion**: transparent — clients who *can* speak Tor reach
  you via the onion automatically without any UI.
- Research-stage: DNS-based discovery, "Sauteed Onions" (CT-log based), onion association
  proposals.

---

## Where to go next

- Copy-paste torrc, control-port and `Onion-Location` configuration: §13 →
  `tor-building-on-tor-software-patterns`.
- Why the guard layer under a service matters so much: §7.1 →
  `tor-network-consensus-guards-and-paths`.
- The deanonymization literature behind §9.1: §11.3 and §11.6 →
  `tor-attack-literature-and-threat-model`.
- Arti's onion-service support and the C tor → Arti decision: §12.1 →
  `tor-ecosystem-alternatives-and-governance`.
