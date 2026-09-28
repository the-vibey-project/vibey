---
id: skill-5-flow-control-congestion-control-and-conflux-f5b8edc8e7
purpose: 5 flow control congestion control and conflux
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-protocol-circuits-and-cell-cryptography/SKILL.md
requires: ["skill-4-circuit-cryptography-from-tap-to-ntor-to-cgo-c06d91466d"]
links: ["skill-where-to-go-next-c292fa5d91"]
---

## §5. Flow control, congestion control, and Conflux

Tor's performance problems were never mainly cryptographic; they're **queueing**. Three
successive systems matter.

### §5.1 Classical flow control: SENDME windows

The original design gives each stream a 50-cell window and each circuit a 100-cell window;
receivers return a `SENDME` acknowledgment every N cells to refill the sender's credit. This
prevents memory overload at exits but says nothing about **congestion inside the network** —
queues built up at slow relays, and the result was Tor's infamous multi-second latency spikes.

### §5.2 Proposal 324: real congestion control (C tor 0.4.7, 2022; tuned through 0.4.8)

Prop 324 adapts TCP-grade algorithms to circuits: **Tor-Westwood** and **Tor-Vegas**
estimators pace cells by measured RTT and bandwidth-delay product, with **NOLA** as a
bandwidth-oracle fallback. Circuit windows can now grow and shrink, and new round-trip
signaling (`XON`/`XOFF`-style flow control cells on the newer subprotocol) replaces some
SENDME behavior. Measured effect: large-file and interactive performance improved markedly,
with much smaller inter-relay queues. In Arti, flow control + congestion control
(`flowctl-cc`) became **stable in 2.4.0 (June 2026)** and always-on with CGO in 2.6.x.

### §5.3 Proposal 329: Conflux (traffic splitting)

Conflux lets a client split one logical stream across **two circuits to the same exit**,
reassembling out-of-order data at the endpoints — head-of-line blocking on one circuit no
longer stalls everything. The relay side adds `RELAY_CONFLUX_LINK`/`LINKED`/`SWITCH` cells and
reorder buffers; scheduling algorithms (MinRTT, LowRTT, BLEST) decide which leg gets the next
cell. Status: **enabled on the live network in C tor since 2024** (controlled by the
`cfx_enabled` consensus parameter), with bug-fix work through 2025–2026 (a non-fatal assertion
fixed in 0.4.8.20; a Conflux queue DoS, CVE-2026-44600, fixed in 0.4.9.7). Benefits are
largest for interactive/bursty traffic. Arti porting was active through 2025 (Arti 1.4.5
changelog) — check release notes for client-side status.

> **⚠️ GOTCHA for onion-service operators:** the legacy Python `vanguards` addon is
> **incompatible with Conflux** (it requires `ConfluxEnable 0`). That is one of the main
> reasons the vanguards path now runs through Arti — see §9.1 →
> `tor-onion-services-and-hardening`.

---
