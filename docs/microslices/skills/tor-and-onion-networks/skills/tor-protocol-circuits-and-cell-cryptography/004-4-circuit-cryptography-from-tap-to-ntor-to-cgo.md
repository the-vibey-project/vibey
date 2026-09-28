---
id: skill-4-circuit-cryptography-from-tap-to-ntor-to-cgo-c06d91466d
purpose: 4 circuit cryptography from tap to ntor to cgo
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-protocol-circuits-and-cell-cryptography/SKILL.md
requires: ["skill-3-the-core-protocol-cells-circuits-and-the-telescoping-handshake-a8a916a770"]
links: ["skill-5-flow-control-congestion-control-and-conflux-f5b8edc8e7"]
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
