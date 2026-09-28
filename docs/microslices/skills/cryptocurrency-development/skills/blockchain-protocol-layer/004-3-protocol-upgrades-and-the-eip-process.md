---
id: skill-3-protocol-upgrades-and-the-eip-process-5b33abdf25
purpose: 3 protocol upgrades and the eip process
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-protocol-layer/SKILL.md
requires: ["skill-2-nodes-and-clients-c48cfe2369"]
links: ["skill-11-layer-2-and-building-a-chain-54ab40b2d8"]
---

## §3. Protocol Upgrades and the EIP Process

### 3.1 How changes happen

```
idea → EIP draft → ACD calls (All Core Devs, Execution + Consensus)
  → devnets → public testnets (Sepolia, Holesky/Hoodi) → MAINNET FORK
```
**EIP tracks**: **Core** (consensus-breaking), **Networking**, **Interface**, and **ERC**
(application-layer standards — §7 → `blockchain-smart-contract-development`). **[DURABLE] ERCs are the ones application developers
care about; Core EIPs are the ones that break your node if you don't upgrade.**

**[DURABLE] Hard forks are coordinated flag days.** Every execution client (Geth,
Nethermind, Besu, Erigon, Reth) and every consensus client (Lighthouse, Prysm, Teku,
Nimbus, Lodestar, Grandine) ships a **mandatory release**, and **testnets always fork
first** — that gap is your window to find problems while they're cheap.

**⚠️ A network upgrade never requires users to "migrate" or "upgrade" their tokens.**
Balances, addresses, and keys are unaffected. **Anyone telling holders to upgrade their ETH
for a fork is running a scam** — and this recurs at every single fork.

### 3.2 The recent and upcoming forks

**[VERSIONED]** Ethereum has settled into a roughly **twice-yearly** cadence:

| Fork | Date | Headline |
|---|---|---|
| **The Merge** | Sept 2022 | PoW → PoS; ~99.95% energy reduction |
| **Shapella** | Apr 2023 | Staking withdrawals |
| **Dencun** | Mar 2024 | **EIP-4844 proto-danksharding** — blobs; cut L2 data costs ~90% |
| **Pectra** | May 2025 | **EIP-7702** (EOAs can act like smart accounts, §7.3 → `blockchain-smart-contract-development`); **EIP-7251** validator consolidation |
| **Fusaka** | **3 Dec 2025** | **PeerDAS** — validators sample blob data instead of downloading all of it; gas limit to ~60M |
| **Glamsterdam** | **targeted 2026** | **EIP-7732 (ePBS)** and **EIP-7928 (Block-Level Access Lists)**; **EIP-7904** gas repricing |
| **Hegotá** | 2027 | **FOCIL** headlining; Verkle discussed |

**⚠️ Glamsterdam's date is genuinely unsettled and the sources conflict** — official
Ethereum roadmap material has listed **Q4 2026**, other coverage has said H1 2026 or "second
half of 2026," and developers consistently stress it depends on testnet validation.
**Treat any specific date as provisional and check Forkcast or ethereum.org.**

**Why Glamsterdam matters to builders**: **Block-Level Access Lists** declare what state a
block touches *before* execution, enabling **parallel transaction execution**; **ePBS**
brings proposer-builder separation into the protocol (currently it depends on out-of-protocol
relays, a real centralization dependency — §8.4 → `blockchain-smart-contract-development`) and lays groundwork for inclusion lists;
and **EIP-7904 reprices gas** to realign costs with actual computational resources, since
many current gas prices were set years ago and no longer reflect modern hardware.

### 3.3 The fee environment has changed

**[VERSIONED, and it invalidates a very common mental model.]** If your assumptions about
Ethereum were formed in 2021–2023, they're out of date. **As of May 2026, standard gas has
run around 0.15 gwei with daily averages near 0.5 gwei** — a basic ETH transfer costing
under a cent, with typical days in the low single-digit cents. **"Ethereum mainnet is too
expensive for most apps" is now a stale default assumption.** Do the gas math for your
actual workload rather than relying on folklore.

---
