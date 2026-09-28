---
id: skill-6-developing-on-bitcoin-89b6bc1d2d
purpose: 6 developing on bitcoin
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-bitcoin/SKILL.md
requires: ["skill-5-mining-economics-in-2026-the-part-nobody-predicts-well-5ab1870986"]
links: ["skill-7-governance-what-the-v30-fight-taught-2025-contested-ca7068edee"]
---

## 6. Developing on Bitcoin

### 6.1 The stack

| Layer | Tools |
|---|---|
| Node | **Bitcoin Core** (`bitcoind` + JSON-RPC + wallet), Electrum servers, self-hosted **Esplora/mempool.space** for indexing |
| Networks for dev | **regtest** (local, mine instantly), **signet** (stable global testnet), **testnet4** (BIP-94's fix for testnet3's difficulty exploits) |
| Wallets/keys (Rust) | **BDK** (Bitcoin Dev Kit): descriptors, PSBT, coin selection, Electrum/Esplora backends |
| JS/TS | **bitcoinjs-lib** (+ tiny-secp256k1), scure-btc-signer |
| Lightning | **LDK** (library), **Core Lightning** (plugin-centric), **LND** (gRPC), Eclair |
| Crypto core | **libsecp256k1** (the consensus-critical library) |

### 6.2 Bitcoin Core versions you should know about

- **v30.0 (7 Oct 2025)** — the controversial one: default `-datacarriersize` went **83 → 100,000 bytes** (effectively uncapped within tx-size limits), multiple `OP_RETURN` outputs per tx now relay, minrelay fee floor cut to **0.1 sat/vB**. **Zero consensus changes — pure policy** ([release notes](https://bitcoincore.org/en/releases/30.0/), [GitHub notes](https://github.com/bitcoin/bitcoin/blob/master/doc/release-notes/release-notes-30.0.md)).
- **v31.0 (19 Apr 2026)** — **cluster mempool** replaced ancestor/descendant accounting (cluster limits: **64 txs / 101 kB**), RBF accepted only if it strictly improves the mempool **feerate diagram**, **CPFP carve-out removed** (use TRUC + sibling eviction), new RPCs `getmempoolcluster` / `getmempoolfeeratediagram`, `-privatebroadcast` (broadcast only over Tor/I2P), `-dbcache` default 450 MiB → **1024 MiB**, fee-estimator floor 0.1 sat/vB, new REST `/rest/blockpart/` ([bitcoin.org 31.0](https://bitcoin.org/en/releases/31.0/), [announcement](https://bitcoincore.org/en/2026/04/19/release-31.0/)).

**If you operate fee-bumping, CPFP, or any mempool-sensitive logic, read the v31 release notes before anything else in this file.** The pre-31 mental model (25-descendant rule etc.) is gone.

### 6.3 The core workflows, with real commands

```bash
# spin up a private chain
bitcoind -regtest -daemon
bitcoin-cli -regtest createwallet "dev"          # descriptor wallet by default
bitcoin-cli -regtest -generate 101               # past coinbase maturity
# inspect the new cluster mempool on a real node (v31+)
bitcoin-cli getmempoolcluster <txid>
bitcoin-cli getmempoolfeeratediagram
```

```python
# Minimal BDK-style flow (Rust; API sketch, pinned to bdk_wallet 2.x semantics)
// 1. Describe the wallet as a descriptor, not keys-in-code
let external = "wpkh(tprv8.../84'/1'/0'/0/*)";
// 2. Build a tx: add recipient, set feerate, enable RBF
// 3. Sign with the wallet's signer set  4. Broadcast via Esplora/Electrum backend
// Everything about change, UTXO selection, and PSBT export is explicit.
```

**The PSBT/multisig workflow** — the one every Bitcoin dev eventually builds: coordinator creates an *unsigned* PSBT from selected UTXOs → each signer signs offline → coordinator combines → finalize → broadcast. Same pattern powers hardware wallets, coinjoin, and Lightning splices.

### 6.4 Bitcoin-dev gotchas

- **[⚠️ Never put keys or seeds in code, env files in git, or CI logs]** — treat libsecp256k1/HSM/KMS boundaries as load-bearing.
- **Fee estimation**: the mempool can fill between broadcast and block; always build with RBF enabled unless you have a reason not to, and know how to CPFP out of a stuck parent (post-31: TRUC rules apply).
- **Descriptor wallet ≠ legacy wallet**: Core dropped legacy wallet creation; use descriptors and `importdescriptors` for watch-only.
- **Verify PSBT fields before signing** — fee, outputs, and derivation paths — on an airgapped or screened device; blind-signing PSBTs is how multisigs get drained.
- **Test against signet before touching real funds; test reorg handling** (`listtransactions` categories change) — indexers that assume no reorgs will lie to you.
- **[DURABLE] timelock foot‑guns**: relative (BIP-68) vs absolute (BIP-65), nSequence semantics — get these wrong and funds are locked or instantly spendable, with no appeal.

---
