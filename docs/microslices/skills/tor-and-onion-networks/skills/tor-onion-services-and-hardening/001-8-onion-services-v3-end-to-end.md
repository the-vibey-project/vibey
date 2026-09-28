---
id: skill-8-onion-services-v3-end-to-end-1df9fb0a83
purpose: 8 onion services v3 end to end
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-onion-services-and-hardening/SKILL.md
requires: []
links: ["skill-9-hardening-onion-services-vanguards-proof-of-work-load-balancing-a0718aa37d"]
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
