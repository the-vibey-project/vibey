---
id: skill-3-upgrades-what-s-shipped-what-s-next-heavily-dated-ee59412b9e
purpose: 3 upgrades what s shipped what s next heavily dated
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-ethereum/SKILL.md
requires: ["skill-2-proof-of-stake-and-the-two-process-node-durable-5419876112"]
links: ["skill-4-using-ethereum-cec8448ef7"]
---

## 3. Upgrades: what's shipped, what's next — heavily dated

| Fork | Date | Headline |
|---|---|---|
| Merge | Sep 2022 | PoW→PoS; ~99.95% energy cut |
| Shapella | Apr 2023 | staking withdrawals |
| Dencun | Mar 2024 | **EIP-4844 blobs** — L2 data costs fell ~90% |
| Pectra | May 2025 | **EIP-7702** (EOAs can execute as smart accounts), EIP-7251 |
| **Fusaka** | **3 Dec 2025** | **PeerDAS** — validators *sample* blob data instead of downloading it all; gas limit ~60M |
| **Glamsterdam** | **targeted Q4 2026 — not confirmed** | ePBS (EIP-7732), **Block-Level Access Lists (EIP-7928)** for parallel execution, state gas repricing (EIP-8037/8038), faster validator exits (EIP-8061), cheaper basic transfers (EIP-2780) |
| Hegotá | 2027 | FOCIL headlining; Verkle discussed |

**Glamsterdam status as of 16 Sep 2026** ([ethereum.org roadmap](https://ethereum.org/roadmap/glamsterdam/), [crypto.news](https://crypto.news/ethereum-targets-oct-6-for-glamsterdam-on-sepolia/)):
- **Sepolia testnet tentatively 6 Oct 2026 (epoch 351232)** — set at ACDC #186 *before* any stable devnet run; Lido and Optimism have asked for a full day of devnet stability plus cross-client fixes first.
- Devnet-8 exposed a consensus bug; devnet-9 had a finality failure; **devnet-11 ran 14 Sept** as the gating test; persistent public devnet "Platåberget" live since Aug.
- **No mainnet date exists.** December 2026 is discussed, aspirational, and entirely test-dependent. Anything claiming a firm date is guessing.
- ⚠️ Numbering churn is real: Aug 2026 materials referenced the state-gas repricing as EIP-7904; current roadmap material uses EIP-8037/8038. When EIPs get renumbered or split pre-fork, that itself is normal process — check [Forkcast](https://forkcast.org) / ethereum.org before writing code against a number.

**Why Glamsterdam matters to builders** ([DURABLE-ish]): BALs declare a block's state reads *before* execution → parallel transaction execution; ePBS brings proposer-builder separation **in-protocol** (today it runs through out-of-protocol MEV-Boost relays — a live centralization dependency) and propagating payloads get ~9s instead of ~2s.

### The fee environment changed — update your priors

If "ETH mainnet is too expensive" was formed in 2021–2023, it's stale. **Mid-September 2026: daily average gas 0.68–0.97 gwei, utilization ~45–56%, average tx fee ~0.0001 ETH (~$0.25); simple transfers at snapshot time cost $0.003–0.006** ([YCharts gas series](https://ycharts.com/indicators/ethereum_average_gas_price), [Etherscan gas tracker](https://etherscan.io/gasTracker)). Do the math for your workload — but do it against current numbers, not folklore.

---
