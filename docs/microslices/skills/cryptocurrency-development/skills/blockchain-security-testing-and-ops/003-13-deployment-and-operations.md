---
id: skill-13-deployment-and-operations-5cbcf79699
purpose: 13 deployment and operations
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-security-testing-and-ops/SKILL.md
requires: ["skill-10-security-804287b292"]
links: []
---

## §13. Deployment and Operations

### 13.1 Deployment

**Checklist**: audited and findings resolved · deployed to a testnet and exercised ·
**exact compiler version pinned** · optimizer settings recorded · **deterministic build
reproducible** · constructor arguments verified · **source verified on the explorer** (§10.3)
· ownership transferred to a multisig/timelock, **not an EOA** · initializers called and
locked · pause mechanism tested · monitoring live · **incident runbook written before
launch**.

**CREATE2** gives deterministic addresses across chains — useful, and note that a
counterfactual address can receive funds before the contract exists.

### 13.2 Key management

**[DURABLE] This is now a first-order security concern rather than an afterthought (§10.1).**
Hardware wallets for anything meaningful. **Multisig (Safe) for protocol control** — and
**verify what you're signing**, since blind signing is how multisig holders get drained.
Timelocks. Separate deploy keys from admin keys from operational keys. **Never put a
private key or mnemonic in a repo, an env file that gets committed, or a CI log** — key
compromise produced the *largest single losses* in 2026's incident data.

### 13.3 Node and validator ops

Client updates on fork deadlines (§3.1 → `blockchain-protocol-layer`) — **fork weeks are when self-managed infrastructure
hurts most**. Run a minority client (§1.3 → `blockchain-protocol-layer`). Monitor sync status, peer count, attestation
effectiveness, and disk headroom. Test on testnets before mainnet forks. **Slashing
protection databases must never be lost or duplicated across machines** — running the same
validator key in two places is the classic self-inflicted slashing.

### 13.4 Indexing and frontends

**[DURABLE] Events are your API to the off-chain world**, and under-emitting is a design
error you'll regret. **Indexers**: The Graph, Ponder, Subsquid, or a custom
`eth_getLogs` + reorg-handling pipeline. **⚠️ Handle reorgs** — data you indexed can be
un-happened, and an indexer that assumes finality too early will serve wrong data.

**Frontend**: viem/wagmi (the current standard), RainbowKit or ConnectKit for wallet
connection, WalletConnect for mobile. **⚠️ Show users what they're signing** in human terms;
opaque signature prompts are the substrate of the phishing losses in §10.1.
