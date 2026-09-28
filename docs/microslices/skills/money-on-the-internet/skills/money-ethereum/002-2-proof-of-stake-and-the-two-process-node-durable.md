---
id: skill-2-proof-of-stake-and-the-two-process-node-durable-5419876112
purpose: 2 proof of stake and the two process node durable
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-ethereum/SKILL.md
requires: ["skill-1-the-mental-model-c002de618f"]
links: ["skill-3-upgrades-what-s-shipped-what-s-next-heavily-dated-ee59412b9e"]
---

## 2. Proof of stake and the two-process node — [DURABLE]

Since **The Merge (Sept 2022)**, Ethereum runs **Gasper**: the **LMD-GHOST** fork choice + **Casper FFG** finality. Blocks arrive every 12 seconds (slots); 32 slots make an epoch; a checkpoint finalizes after two epochs (~13 min) once 2/3 of staked ETH attests. **Slashing** destroys stake for provable equivocation; **inactivity leaks** bleed offline validators during non-finality. Validators stake 32 ETH; **EIP-7251 (Pectra, May 2025)** raised the effective max to 2,048 ETH to allow consolidation.

**Running a node = running two processes**: a **consensus client** (Lighthouse, Prysm, Teku, Nimbus, Lodestar, Grandine) and an **execution client** (Geth, Nethermind, Reth, Besu, Erigon, ethrex), joined by the Engine API. ⚠️ **Client diversity is a systemic risk**: >1/3 of stake on one client can halt finality; >2/3 could finalize an *invalid* chain. This is not theoretical — **Reth suffered a network-wide outage on 2 Sept 2025** processing a specific block; multi-client operators stayed up. As of Aug 2026 verification, EL diversity had genuinely improved (Geth ~36–41% by various measures, Nethermind ~23–32%, Reth ~14–15%) — ⚠️ sources disagree substantially because they measure different populations; one 2026 staking survey put Nethermind ~45% among stakers. **If you stake, run a minority client.**

---
