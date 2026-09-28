---
id: skill-3-the-core-protocol-cells-circuits-and-the-telescoping-handshake-a8a916a770
purpose: 3 the core protocol cells circuits and the telescoping handshake
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-protocol-circuits-and-cell-cryptography/SKILL.md
requires: ["skill-2-history-and-lineage-c8a8e66c92"]
links: ["skill-4-circuit-cryptography-from-tap-to-ntor-to-cgo-c06d91466d"]
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

```
// Outbound (client → destination)
Client builds:  Layer1(Layer2(Layer3(payload)))
Guard:  strips Layer1 → forwards Layer2(Layer3(payload)) to middle
Middle: strips Layer2 → forwards Layer3(payload)         to exit
Exit:   strips Layer3 → forwards payload                 to destination

// Inbound (destination → client) reverses: exit adds Layer3, middle adds Layer2,
// guard adds Layer1, and the client — holding keys for all three hops — strips all three.
```

This is the whole reason the client must hold keys for every hop and each hop holds keys only
for itself: the client is the only party that can construct or unwrap the full stack.

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
