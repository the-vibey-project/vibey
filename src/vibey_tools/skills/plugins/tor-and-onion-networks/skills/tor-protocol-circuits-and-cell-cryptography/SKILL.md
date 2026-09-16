---
name: tor-protocol-circuits-and-cell-cryptography
description: "Use when reasoning about how Tor actually works on the wire — cells, channels, the telescoping circuit handshake, ntor and ntor-v3, the tor1 → CGO cell-crypto migration, SENDME flow control, congestion control and Conflux — or when correcting a claim about what Tor promises. Covers §1–§5. Companion to the other Tor and onion-network skills."
---

# Tor: What It Promises, How Circuits Are Built, and What Encrypts a Cell

> **Part 1 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §1–§5. Sibling skills: `tor-network-consensus-guards-and-paths` (§6–§7),
> `tor-onion-services-and-hardening` (§8–§9),
> `tor-censorship-circumvention-and-bridges` (§10),
> `tor-attack-literature-and-threat-model` (§11),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-building-on-tor-software-patterns` (§13.1–§13.4, handbook §1),
> `tor-running-relays-bridges-and-hardware` (§13.5, handbook §2–§6).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **Currency:** compiled 16 September 2026. Protocol fundamentals (cell formats, handshake
> math) are stable and change slowly. **Version numbers and deployment status are dated** —
> the tor1 → CGO transition in §4 and the Conflux rollout in §5 are mid-flight, so verify
> against <https://spec.torproject.org/> before relying on them months from now.

> **⚠️ A low-latency anonymity overlay: three independently operated relays and layered
> encryption, so no single party links who you are to what you are doing.**
>
> **⚠️ GOTCHA** boxes mark where the mental model people carry is wrong in ways that cause
> real deanonymization or broken tooling.
>
> **The three ideas that organize this document:**
> 1. **⚠️ TOR SEPARATES IDENTIFICATION FROM ROUTING** (§1, §3). **The guard knows who you
>    are but not what you do; the exit knows what you do but not who you are. Every design
>    decision downstream — guards, families, path restrictions — exists to keep those two
>    facts in different hands.**
> 2. **⚠️ THE TLS BETWEEN RELAYS IS NOT THE ANONYMITY LAYER** (§3.3). **Hop-to-hop TLS
>    protects against someone sitting between relays. The anonymity comes from the
>    onion-encrypted relay cells riding inside it. Confusing the two is the most common
>    architectural misreading of Tor.**
> 3. **⚠️ TOR'S PERFORMANCE PROBLEM WAS NEVER CRYPTOGRAPHIC — IT WAS QUEUEING** (§5).
>    **Twenty years of latency complaints came from unmanaged queues at slow relays, which
>    is why the 2022–2026 work is congestion control and traffic splitting, not faster
>    ciphers.**

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

## §2. History and lineage

| Era | Development |
|---|---|
| Mid-1990s | Onion routing invented at the U.S. Naval Research Laboratory (Paul Syverson, David Goldschlag, Michael Reed). The insight: separate *identification* from *routing* by nesting encrypted hops. |
| 2002 | First-generation onion routing prototype deployed at NRL. |
| 2003–2004 | Roger Dingledine, Nick Mathewson, and Paul Syverson build the second-generation system — "Tor" — fixing the first gen's problems (no directory system, replay/integrity weaknesses, usability). The USENIX Security 2004 paper *Tor: The Second-Generation Onion Router* remains the canonical design document. |
| 2004–2006 | EFF funds early development; the network opens to the public. |
| Dec 2006 | The Tor Project, Inc. founded as a U.S. 501(c)(3) nonprofit. |
| 2008–2011 | Tor Browser Bundle (originally "Torbutton") makes the system usable by non-experts; bridges introduced to counter blocking in Iran and China. |
| 2013–2014 | Snowden-era scrutiny and usage spike; ntor replaces the old RSA/TAP handshakes for circuit extension; hidden-service deanonymization research (and at least one real-world attack campaign that surfaced in 2014) catalyzes the v3 redesign. |
| 2015–2018 | `.onion` registered as a special-use domain (RFC 7686); v3 onion service spec written (224/225 proposals era); ed25519 relay identities roll out. |
| 2017 | Directory authority diversity pushed; Tor Browser 7 based on Firefox ESR 52 brings multiprocess. |
| Oct 2021 | v2 onion services (16-char, RSA-1024, SHA-1-derived) **removed from the network**. All onion services are now v3 (56-char). |
| 2022–2023 | Congestion control (proposal 324) ships in C tor 0.4.7 and is tuned through 0.4.8; Conflux traffic-splitting (proposal 329) developed. |
| 2023 | Onion-service proof-of-work DoS defense (proposal 327) ships in tor 0.4.8 (Aug 2023). |
| 2024 | Conflux enabled network-wide in C tor (controlled by consensus parameter); Arti (the Rust rewrite) reaches **client-side feature parity** and gets native vanguards. Tor Project and Tails merge organizations. WebTunnel transport introduced. |
| 2025 | Tor 0.4.9 alphas introduce **CGO cell crypto** and **happy families**; Tor Browser 15 (Firefox ESR 140); Arti 2.x series begins; Tor VPN beta (Arti-based Android VPN); Conflux hardening continues; Tails 7 (Debian 13) and Qubes 4.3 ship. |
| 2026 (as of Sept) | C tor 0.4.9.5 is the first stable 0.4.9 (12 Feb 2026); the 0.4.8 series is on the deprecation path. Arti 2.6.0 (1 Sept 2026) makes CGO and congestion control always-on, and pushes toward **Arti-as-relay** (directory mirror, DNS streams, channel auth). |

**⚠️ The pattern to internalize:** **C tor is in managed decline, Arti is the future.** In
2026 the frontier work is relay/directory-authority support in Arti + post-SHA-1 cell crypto
(CGO) + congestion/flow-control modernization.

---

## §3. The core protocol: cells, circuits, and the telescoping handshake

Everything in Tor happens in **cells** — fixed-size messages multiplexed over TLS connections
("channels") between relays. The classic cell is 514 bytes on the wire: a 2-byte circuit ID
(4 bytes on modern link protocols), a 1-byte command, and a 509-byte payload. Variable-length
cells exist for protocol negotiation and directory data.

Cell commands split into two families:

- **Channel-level:** `CREATE`/`CREATED` (now `CREATE2`/`CREATED2`), `DESTROY`, `NETINFO`,
  `CERTS`, `AUTH_CHALLENGE`/`AUTHENTICATE`, `PADDING` — negotiated directly with the
  immediate neighbor.
- **Circuit-level:** `RELAY` (and `RELAY_EARLY` near circuit creation) — onion-encrypted
  payloads that tunnel *through* the channel, understood only by whichever hop peels that
  layer.

### §3.1 How a circuit is built ("telescoping")

1. **Client → Guard.** The client performs an authenticated ntor key exchange (`CREATE2`)
   with its chosen guard. Both sides now share a symmetric key pair (forward/backward
   digests) for that hop. Result: circuit hop 1.
2. **Extend to hop 2.** The client builds an `EXTEND2` relay cell containing the link
   specifiers of the middle relay plus a fresh ntor handshake blob, onion-encrypted for the
   guard. The guard unwraps, opens (or reuses) a channel to the middle, forwards the
   handshake, and returns the middle's `CREATED2` response inside an `EXTENDED2` relay cell.
   The client now has shared keys with hop 2 as well — negotiated *through* hop 1 without hop
   1 learning the hop-2 key.
3. **Extend to hop 3 (exit).** Same procedure, now layered through hops 1 and 2.

Each hop strips one layer of symmetric crypto from outbound cells and adds one layer to
inbound cells — the "onion." The exit decrypts the final layer and forwards plaintext to the
destination (for client circuits) or the service.

Two safety rails worth knowing:

- **`RELAY_EARLY` cells** bound circuit construction: only the first N (8) relay cells in a
  circuit's life may extend it, which prevents infinitely long circuits being used as a
  resource-exhaustion vector and bounds certain tagging/confirmation games.
- Circuit IDs scope cells within a channel; `NETINFO` cells exchange timing/address data used
  for NAT traversal and address confirmation.

### §3.2 Streams

Once a circuit exists, the client attaches **streams** (TCP connections) to it with
`RELAY BEGIN`; the exit answers `CONNECTED`. Data flows as `RELAY DATA` cells; `RELAY END`
closes a stream. Tor multiplexes many streams over one circuit, and one client's circuits may
carry arbitrarily many streams — but see **stream isolation** (§13.1 →
`tor-building-on-tor-software-patterns`) for why Tor Browser splits streams by first-party domain
anyway.

### §3.3 ⚠️ GOTCHA: where the TLS ends

A subtlety newcomers miss: the hop-to-hop transport is TLS over TCP, but that TLS only
protects against attackers sitting *between* relays — it is **not** the anonymity layer. The
anonymity comes from the onion-encrypted relay cells riding inside. Relay channels
authenticate with ed25519 identities (since the 0.3.0 era), and as of C tor 0.4.9 (Feb 2026)
the last pre-ed25519 link authentication methods (v1/v2 handshakes, the old
`RSA-SHA256-TLSSecret` auth) were **removed**, along with fake-TLS cipher advertisement code.

---

## §4. Circuit cryptography: from TAP to ntor to CGO

### §4.1 The handshake stack

| Generation | Used for | Status (Sept 2026) |
|---|---|---|
| TAP | RSA-1024 + DH-1024 first-hop create, old extend | **Fully removed** from C tor in 0.4.9 (2026) |
| ntor | Curve25519/X25519 one-way-authenticated key exchange for `CREATE2`/`EXTEND2`; variant `hs-ntor` for onion-service intro/rendezvous handshakes | Standard, universal |
| **ntor-v3** | Extended ntor with authenticated client→server data in the handshake (needed by CGO's crypto negotiation) | Rolling out; required for CGO negotiation |

The ntor design (Goldberg–Stebila–Ustaoglu, 2012–2013) gives **one-way authentication in a
single round trip**: the server proves identity via its long-term key, the client stays
anonymous, and both derive forward-secret session keys. The cost that motivated it — the old
TAP handshake needed full RSA operations per hop and was CPU-dominant for relays — is why
modern Tor scales at all.

### §4.2 The cell crypto itself: "tor1" and its replacement

For two decades the relay-level symmetric crypto ("tor1") was AES-128 in counter mode plus a
4-byte running SHA-1 digest for integrity. Cryptographers flagged its problems for years:

- **Tagging attacks.** CTR mode is malleable: a hop (or observer who controls a hop) can flip
  predictable bits in a cell and watch the effect emerge at another hop — a marked cell
  becomes a tracking beacon through the circuit.
- **Weak integrity.** Four bytes of digest is ~32-bit authentication, and the underlying hash
  was SHA-1.
- **No forward secrecy at the cell layer** — keys stayed constant for the life of the circuit.

The replacement, **Counter Galois Onion (CGO)**, designed by Degabriele, Melloni, Münch and
Stam (proposal 308, 2019; revised and instantiated as **proposal 359, "CGO Redux"**), is the
biggest change to Tor's wire format since v3 onion services:

- Built on **UIV+**, a *rugged pseudorandom permutation*: encryption is non-malleable (any
  tamper, and that cell *plus every subsequent cell in that direction* becomes unrecoverable
  — killing tagging), while relays process cells via a deliberately malleable decrypt path.
- Primitives are AES-128 (counter PRF) + **POLYVAL** universal hashing — chosen to exploit
  AES-NI and PCLMULQDQ hardware instructions, so the security upgrade is also fast on modern
  server CPUs.
- Cell format becomes a **16-byte authenticator tag + 493-byte body**; the running SHA-1
  digest and the `Recognized` field disappear (SENDMEs now bind to the cell tag).
- Keys **evolve per cell** (`UPDATE_UIV`), so old cells can't be re-decrypted later even with
  the current key — forward secrecy at the cell layer.
- **Deployment status (Sept 2026):** implemented in C tor 0.4.9 (clients and relays negotiate
  it) and in Arti, where CGO + congestion control became **always-on in Arti 2.6.0 (1 Sept
  2026)**, after being marked stable in Arti 2.5.0 (30 June 2026). It requires ntor-v3 and the
  new FlowCtrl congestion signaling — which is why it arrived together with the flow-control
  redesign below. Onion-service-circuit CGO was in experimental stabilization in Arti 2.5.x
  (mid-2026).

> **⚠️ GOTCHA for tooling authors:** this is still a *negotiated* transition. Mixed networks
> run tor1 and CGO side by side until client/relay adoption saturates. When reading packet
> traces or writing parsers, expect **both formats on the wire** through at least the rest of
> 2026 — a parser that assumes the 4-byte SHA-1 digest, or one that assumes the 16-byte tag,
> will silently mis-frame half the network.

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

## Where to go next

- The relays, the nine directory authorities, consensus mechanics and guard pinning:
  §6–§7 → `tor-network-consensus-guards-and-paths`.
- v3 onion services, vanguards and proof-of-work: §8–§9 →
  `tor-onion-services-and-hardening`.
- Bridges, pluggable transports and the 2025–2026 censorship arms race: §10 →
  `tor-censorship-circumvention-and-bridges`.
- What actually deanonymizes people: §11 → `tor-attack-literature-and-threat-model`.
- Specs, proposals and the foundational papers: §16 →
  `tor-ecosystem-alternatives-and-governance`.
