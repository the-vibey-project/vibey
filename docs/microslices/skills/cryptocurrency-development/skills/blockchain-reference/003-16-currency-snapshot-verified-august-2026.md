---
id: skill-16-currency-snapshot-verified-august-2026-155d46963e
purpose: 16 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-reference/SKILL.md
requires: ["skill-15-contested-questions-9ccfe96fc7"]
links: ["skill-17-the-canon-600cf8c87f"]
---

## §16. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Fusaka** | **Activated 3 December 2025.** **PeerDAS** — validators sample blob data by column across 128 subnets rather than downloading every blob; gas limit raised to ~60M | Low |
| **Glamsterdam** | ⚠️ **Date genuinely unsettled** — ethereum.org's roadmap has listed **Q4 2026**; other coverage says H1 2026 or "second half of 2026"; a June 2026 report described it at the all-EIP devnet stage, "the final phase before public testnet." Headline EIPs: **EIP-7732 (ePBS)**, **EIP-7928 (Block-Level Access Lists)**, **EIP-7904 (gas repricing)**. Goals: parallel execution, in-protocol block building, higher L1 capacity. **Check Forkcast for status** | **High** |
| **Hegotá** | Named December 2025; targeted **2027**. **FOCIL** (Fork-Choice enforced Inclusion Lists) selected as the headline feature; **Verkle Trees** under discussion | **High** |
| **Pectra** | May 2025. **EIP-7702** (EOAs execute as smart contracts) and **EIP-7251** (validator max effective balance to 2048 ETH) | Low |
| **Gas environment** | ⚠️ **As of 5 May 2026, standard gas around 0.15 gwei, daily averages near 0.5 gwei through April** — basic transfers under a cent. **The 2021–2023 fee regime is not a safe default assumption** | Medium |
| **Solidity** | **0.8.36 (9 July 2026)** latest stable — included **two medium-severity security fixes**; 0.8.37 in nightly. Experimental **SSA-form code generator** (introduced 0.8.35) gaining stack-to-memory improvements | Medium |
| **Execution client share** | ⚠️ **Sources disagree by measurement method.** Ethernodes (peer-visible): **Geth ~41%, Nethermind ~32%, Reth ~15%, Besu ~7%, Erigon ~2%**. Chainstack: Geth 36%, Nethermind 23%, Reth 13.9%, Besu 11.9%, Erigon 4.5%. A 2026 EthStaker survey of its community: **Nethermind ~45%, Geth ~33%, Besu ~15%**. Geth is down from a historic ~84% | Medium |
| **Client incidents** | **2 September 2025: a critical issue took down most Reth nodes on mainnet** at block 23272427. Multi-client operators stayed up. **The case for diversity is empirical, not theoretical** | Low |
| **ZK in clients** | **Nethermind** building ZK proving into the production execution client (execution witness capture, stateless replay, minimal EVM binary complete); **ethrex** (LambdaClass, Rust) runs the same codebase as an L1 client *and* a multi-prover ZK rollup | Medium |
| **Hardhat 3** | Major rewrite: new **EDR** engine, **native Solidity tests**, multichain/OP Stack simulation, gas statistics, rebuilt config. Benchmarks put it **within ~2× of Foundry vs. Hardhat 2's 10–20× penalty**. Cross-tool interop: `foundry.toml` parsed by Hardhat, shared artifacts | Medium |
| **Loss categories (OWASP SC Top 10 2026, from 2025 data)** | **149 incidents, ~$1.42B total. Access control $953.2M · logic errors $63.8M · reentrancy $35.7M · flash loans $33.8M.** ⚠️ Access control leads by more than an order of magnitude | Medium |
| **The 2026 shift** | ⚠️ **Smart contract exploit losses fell ~89% YoY in Q1 2026 (DefiLlama) — and total losses stayed high.** ~$450M across 145 incidents in Q1, of which **phishing and social engineering were ~$306M (≈2/3)**. One January social-engineering attack drained **$282M with no code exploited**. Six audited protocols breached that quarter; **one had 18 prior audits** | **High** |
| **Threat actors** | **Chainalysis attributes ~76% of 2026 crypto hack losses to state-backed actors linked to Lazarus Group**; DPRK cumulative attributed theft exceeds $6B since 2017. Methods include multi-month social engineering and embedding operatives as IT workers | Medium |
| **Unverified contracts** | Chainalysis found **five protocols in six months where the exploited contract was the protocol's own and unverified**, ~$36.7M combined. Also notes **AI-assisted exploit development is likely accelerating** | Medium |
| **Audit costs** | ~**$3,000** for a simple contract to **$100,000+** for complex multi-contract systems. **Formal verification** (Certora Prover, Halmos) increasingly a standard offering rather than a premium add-on | Medium |

**Goes stale fastest:** Glamsterdam's date and scope; client share numbers; exploit
statistics; Solidity patch versions. **Essentially never stale:** §4 → `blockchain-smart-contract-development` (EVM model), §6.3 → `blockchain-smart-contract-development`
(design principles), §7.1 → `blockchain-smart-contract-development` (ERC-20 misbehaviours), §8.2 → `blockchain-smart-contract-development`–8.3 (oracles and flash loans),
§10.2 → `blockchain-security-testing-and-ops` (the vulnerability canon), §14 (anti-patterns).

---
