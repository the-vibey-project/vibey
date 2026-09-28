---
id: skill-11-layer-2-and-building-a-chain-54ab40b2d8
purpose: 11 layer 2 and building a chain
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-protocol-layer/SKILL.md
requires: ["skill-3-protocol-upgrades-and-the-eip-process-5b33abdf25"]
links: ["skill-12-cross-chain-a5e9cc9aa6"]
---

## §11. Layer 2 and Building a Chain

### 11.1 The rollup model

**[DURABLE]** Execute off-chain, post data and proofs to L1, inherit L1 security for data
availability and settlement.

| Type | Validity | Withdrawal | Notes |
|---|---|---|---|
| **Optimistic** | Assumed valid; **fraud proofs** during a challenge window | **~7 days** (or fast via a liquidity provider) | OP Stack, Arbitrum. Simpler; the delay is the cost |
| **ZK / validity** | **Validity proof** verified on L1 | Minutes to hours | zkSync, Starknet, Scroll, Linea, Polygon zkEVM. Proving cost and complexity are the trade |
| **Validium / volition** | Validity proof, **data off-chain** | Fast | Cheaper; **weaker data-availability guarantees** |

**[DURABLE] The security question for any L2 is always the same three things**: who can
censor you, who can steal from you, and can you exit without permission? **L2Beat's stage
classification** is the honest scoring of exactly that, and it's the right first stop before
trusting any chain's marketing.

**⚠️ The centralized sequencer is the current reality.** Most rollups rely on a single
sequencer to order and execute transactions — a censorship risk and single point of failure.
**Forced-inclusion via L1 is the escape hatch**, and you should verify it exists and works.
**Decentralized sequencer designs are under active development but remain largely
unshipped.**

**Blobs (EIP-4844) are how L2 data gets cheap**, and **PeerDAS (Fusaka)** is what lets blob
capacity grow — validators sample columns rather than downloading every blob in full.

### 11.2 Building a chain

**[DURABLE] Ask first whether you need one.** A new chain means bootstrapping validators or
sequencers, liquidity, bridges, tooling, indexers, wallets, and users — and fragmenting
liquidity is usually a larger cost than whatever it buys.

If you do: **rollup-as-a-service stacks** (OP Stack, Arbitrum Orbit, ZK Stack, Polygon CDK,
Starknet's stack) are how most L2s are built now. **Cosmos SDK / CometBFT** for a sovereign
app-chain. **Polkadot parachains.** Fully custom is a multi-year effort.

**[VERSIONED] The client layer is adapting to this**: Nethermind implements each supported
L2 as a plugin with an OP Stack rollup node built directly into the client (replacing a
separate `op-node`), and **ethrex** is a Rust client whose same codebase runs as both an L1
execution client and a multi-prover ZK-rollup. **ZK-proving is being built into production
execution clients**, which is a meaningful shift in what a "client" is.

---
