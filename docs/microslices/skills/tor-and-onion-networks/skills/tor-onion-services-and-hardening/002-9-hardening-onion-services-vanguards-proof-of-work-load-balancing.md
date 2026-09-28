---
id: skill-9-hardening-onion-services-vanguards-proof-of-work-load-balancing-a0718aa37d
purpose: 9 hardening onion services vanguards proof of work load balancing
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-onion-services-and-hardening/SKILL.md
requires: ["skill-8-onion-services-v3-end-to-end-1df9fb0a83"]
links: ["skill-where-to-go-next-3478343df8"]
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

### §9.5 Deployment checklist for a private onion service

Every item here is argued elsewhere in §8–§9 and §13; this is the order to do them in.

1. Run tor from the **Tor Project's own repository**, not the distro's (fresher).
2. **v3 only** — v2 left the network in October 2021 (§8.4).
3. **Generate the master identity key offline**; deploy only signing material, and set
   `OfflineMasterKey`.
4. **PoW** if DoS is a concern (§9.2). **Vanguards** for guard-discovery resistance (§9.1 —
   Arti has them built in; the C tor Python addon is unmaintained and incompatible with
   Conflux).
5. **Client authorization** for private services (§8.3, §13.3 →
   `tor-building-on-tor-software-patterns`).
6. **MetricsPort** for monitoring.
7. **Test descriptor publication from a second tor instance** before you hand the address to
   anyone.
8. Advertise via **Onion-Location** if you have a clearnet twin — and **never serve the
   Onion-Location header from the onion itself** (§9.4).

---
