---
id: skill-2-nodes-and-clients-c48cfe2369
purpose: 2 nodes and clients
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-protocol-layer/SKILL.md
requires: ["skill-1-the-protocol-layer-a8e23e2532"]
links: ["skill-3-protocol-upgrades-and-the-eip-process-5b33abdf25"]
---

## §2. Nodes and Clients

### 2.1 Node types

| Type | Stores | Use |
|---|---|---|
| **Full node** | Current state + recent history; verifies everything | The default. What you should run |
| **Archive node** | All historical state at every block | Analytics, indexers, `eth_call` at old blocks. **Very large** |
| **Light client** | Headers + proofs | Mobile, embedded; the Verge roadmap's target |
| **Validator** | Full node + consensus client + signing keys | Staking |

**[VERSIONED] Reth is notably fast to sync** — substantially faster than Geth's baseline on
equivalent NVMe hardware. **NVMe SSD is non-negotiable** for any client; spinning disks and
most SATA SSDs cannot keep up with state access patterns.

### 2.2 Working with nodes

**JSON-RPC** is the universal interface: `eth_call` (simulate, no state change),
`eth_estimateGas`, `eth_sendRawTransaction`, `eth_getLogs` (⚠️ heavily rate-limited by
providers and the usual source of "why is my indexer slow"), `eth_getStorageAt`,
`debug_traceTransaction` (⚠️ archive/debug-enabled nodes only, and the most useful
debugging tool you have).

**Libraries**: **viem** (TypeScript — the modern default, better typing and DX than its
predecessor), **ethers.js** (still widely used), **web3.js** (legacy), **web3.py**,
**Alloy** (Rust — the Foundry/Reth ecosystem's stack), **Nethereum** (.NET), **web3j** (Java).

**⚠️ Running your own node vs. using a provider is a real architectural decision**, not a
purity question. Providers (Alchemy, Infura, QuickNode, Chainstack) are operationally
simpler; your own node removes a trust and censorship dependency and removes rate limits.
**Anything that must not be censorable should not depend on one provider.**

---
