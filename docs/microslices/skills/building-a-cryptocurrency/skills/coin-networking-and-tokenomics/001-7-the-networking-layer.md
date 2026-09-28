---
id: skill-7-the-networking-layer-c4802ba0de
purpose: 7 the networking layer
source: src/vibey_tools/skills/plugins/building-a-cryptocurrency/skills/coin-networking-and-tokenomics/SKILL.md
requires: []
links: ["skill-8-economics-and-tokenomics-9d091dddba"]
---

## §7 The Networking Layer

A cryptocurrency is a peer-to-peer network. **There is no central server.** Nodes discover each
other, maintain connections, gossip transactions and blocks, and independently validate
everything they receive. The networking layer is often underappreciated but is critical to the
system's resilience.

### P2P architecture

**Discovery.** Nodes find peers through three mechanisms:

| Mechanism | How it works |
|---|---|
| DNS seed lists | Hardcoded hostnames that resolve to known node IP addresses |
| Hardcoded IP lists | Fallback when DNS seeds are unavailable |
| Peer exchange | Nodes tell each other about other nodes they know |

New nodes bootstrapping onto the network use these mechanisms to find their first connections.

**Message types.** The wire protocol is a small set of messages:

| Message | Purpose |
|---|---|
| Version handshake | Negotiate protocol version and capabilities |
| `addr` | Share peer addresses |
| `inv` | Announce new transactions or blocks **by hash** — the recipient requests full data only if they do not already have it |
| `getdata` | Request the full payload for an announced hash |
| `tx`, `block` | Full payload |
| `ping` / `pong` | Keepalive and latency measurement |

The `inv` → `getdata` split is the bandwidth-saving core of the design: announce the hash
first, transfer the object only on demand.

**Block propagation.** When a miner finds a block, they broadcast it to their peers, who
validate it and relay it to their peers. **Compact block relay (BIP-152)** sends only the block
header and short transaction IDs, letting peers that already have most transactions
reconstruct the block without downloading full transactions they already know. This
minimizes bandwidth and reduces the time for blocks to propagate globally — important
because **slow propagation increases orphan rates and centralization pressure**. A miner who
hears about a block late wastes work on a stale tip; large, well-connected miners suffer that
less, which is why propagation latency is a decentralization problem and not merely a
performance one.

**Mempool.** Each node maintains a mempool of valid but unconfirmed transactions. When a
node receives a transaction it validates it — proper signatures, inputs exist and are unspent,
no double-spend — and if valid, adds it to the mempool and relays it. Miners select
transactions from their mempool to include in blocks, typically prioritizing by **fee rate
(satoshis per virtual byte)**.

> **The mempool is not shared state.** Each node has its own, and they can differ based on
> relay policy. Do not design anything that assumes two nodes see the same set of pending
> transactions.

### POLICY VS. CONSENSUS

What a node will **relay** (policy) and what the network will **accept in a block** (consensus)
are different rule sets. A node might refuse to relay transactions with very low fees, but still
accept a block containing them.

This distinction is **the actual constitution of blockchain governance** — policy changes can
split the mempool without splitting the chain. Bitcoin's 2025 v30 fight over `OP_RETURN`
defaults was a policy change, not a consensus change, and it was the sharpest governance
clash since the block-size wars.

Design consequence: a policy knob is a low-stakes lever you can turn per node and ship
without coordination; a consensus rule is a fork. Know which one you are touching before you
change a default.
