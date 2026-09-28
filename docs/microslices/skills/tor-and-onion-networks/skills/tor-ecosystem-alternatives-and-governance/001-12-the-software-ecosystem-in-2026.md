---
id: skill-12-the-software-ecosystem-in-2026-cd28e53516
purpose: 12 the software ecosystem in 2026
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-ecosystem-alternatives-and-governance/SKILL.md
requires: []
links: ["skill-14-tor-vs-the-alternatives-i2p-mixnets-vpns-9309c7745e"]
---

## §12. The software ecosystem in 2026

### §12.1 The two Tor implementations

- **C tor** (the `tor` daemon): remains the **only implementation that can operate relays,
  bridges, exits, and HSDirs**. Current stable **0.4.9.x** (0.4.9.5, first stable, Feb 2026);
  0.4.8.x deprecated path. New in 0.4.9: CGO negotiation, happy families, TAP removal,
  `ReevaluateExitPolicy`, exit-side stream DoS limiting (`DoSStream*`), Monero ports in the
  reduced exit policy, exit-DNS TTL clipping (cache-oracle mitigation).
- **Arti** (Rust): client-parity (since 1.3.0, late 2024); production onion services (1.8.0
  removed the disclaimer, Dec 2025); 2.x series through 2026 — HTTP CONNECT proxy (2.2),
  stable flowctl-cc (2.4, June 2026), **CGO stable (2.5, June 2026) and always-on (2.6, Sept
  2026)**, unix-socket onion-service backends, `arti hsc ctor-migrate` for C-tor→Arti key
  migration, and active **relay / directory-mirror / directory-authority** development — the
  declared frontier for 2026–2027. Embeddable as `arti-client` / `arti-hyper` crates; an
  **Arti RPC** interface is in development; **onionmasq** (tun-over-Tor virtual interface)
  powers Tor VPN and is the cleanest "route arbitrary apps through Arti" path.

### §12.2 End-user platforms

- **Tor Browser 15.x** (Oct 2025 stable; Firefox ESR 140): vertical tabs/tab groups,
  security-level rework, NoScript-managed WebAssembly. Tor Browser 16 (mid-2026 cycle)
  requires Android 8.0+ and drops x86. On Android the browser is GeckoView-based.
- **Tor VPN (beta, Android; 2025–2026)**: Arti-based per-app VPN — each app gets its own
  circuit (stream isolation as the product), WebTunnel bridges, reproducible builds,
  Cure53-audited (June 2025). **Not for high-risk users while in beta.**
- **Orbot** (Android), **Onion Browser** (iOS, Tor.framework), **Briar** (P2P messaging over
  onion services), **OnionShare** (ephemeral onion services UX) — all embed tor/Arti via
  libraries like IPtProxy (`obfs4proxy`, snowflake Go bindings).
- **Tails 7.x** (Sept 2025, Debian 13 Trixie; organizationally now part of the Tor Project):
  amnesic live USB — nothing persists unless you opt in; all traffic forced through Tor with
  fail-closed firewalls.
- **Whonix 18** (with **Qubes OS 4.3**, Dec 2025): two-VM isolation model — Gateway (Tor-only,
  routes) + Workstation (can *only* reach the gateway), so even a fully exploited Workstation
  cannot reveal the real IP. Physical Whonix = two machines.

> **⚠️ GOTCHA — iOS:** Onion Browser is constrained by iOS process rules, notably the WebRTC
> leak class, and it has no control over Safari-level leaks. Treat iOS Tor as **best-effort**,
> not equivalent to Tor Browser on desktop.

### §12.3 Operator and developer tooling

- **nyx** — terminal monitor for relays/services.
- **stem** — the canonical Python control-port library; **unmaintained since ~2020 but still
  the standard** (Damian Johnson: "unmaintained, not deprecated — the only game in town");
  1.8.1 (Oct 2022) latest. Async alternatives: **txtorcon** (Twisted), **aiostem** (asyncio).
- **chutney** — spins up a whole private Tor network on localhost for integration testing. If
  you build on Tor, this is your test harness.
- **onionspray / onionbalance / MetricsPort-Prometheus** — service-scale and observability
  stack.
- **check.torproject.org** (`/api/ip`) — the official "am I exiting via Tor?" oracle for
  leak-testing your own plumbing.

---
