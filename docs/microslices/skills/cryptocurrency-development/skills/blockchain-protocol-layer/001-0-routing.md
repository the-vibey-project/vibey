---
id: skill-0-routing-92a8c8081a
purpose: 0 routing
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-protocol-layer/SKILL.md
requires: []
links: ["skill-1-the-protocol-layer-a8e23e2532"]
---

## §0. Routing

### 0.1 Two very different jobs

**[DURABLE] "Crypto development" means two largely disjoint skill sets**, and conflating
them is the most common orientation error:

| | **Protocol development** | **Application development** |
|---|---|---|
| You build | Clients, consensus, VMs, L2 stacks, cryptography | Smart contracts and the systems around them |
| Languages | Go, Rust, C#, Java, Zig, Nim | Solidity, Vyper, Huff, Yul |
| Failure mode | Chain splits, finality failures, mass slashing | Drained contracts |
| Review culture | Multi-client testing, devnets, spec conformance | Audits, fuzzing, formal verification |
| Sections | §1, §2, §3, §11, §12 | §4–§10 → `blockchain-smart-contract-development`, `blockchain-security-testing-and-ops`, §13 → `blockchain-security-testing-and-ops` |

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Consensus, finality, the protocol layer | §1 |
| Ethereum clients and node operation | §2 |
| The upgrade process, EIPs, hard forks | §3 |
| The EVM execution model, gas, storage | §4 → `blockchain-smart-contract-development` |
| Solidity and the contract languages | §5 → `blockchain-smart-contract-development` |
| Contract architecture: proxies, upgrades, access control | §6 → `blockchain-smart-contract-development` |
| Standards: ERC-20/721/1155/4626, account abstraction | §7 → `blockchain-smart-contract-development` |
| DeFi primitives, oracles, MEV | §8 → `blockchain-smart-contract-development` |
| Testing: Foundry, Hardhat, fuzzing, formal verification | §9 → `blockchain-security-testing-and-ops` |
| Security: the vulnerability canon and what actually loses money | §10 → `blockchain-security-testing-and-ops` |
| L2s, rollups, and building a chain | §11 |
| Cross-chain and bridges | §12 |
| Deployment, keys, ops, indexing, frontends | §13 → `blockchain-security-testing-and-ops` |
| Interpretability of on-chain data, analytics | §13.4 → `blockchain-security-testing-and-ops` |
| "Don't do this" | §14 → `blockchain-reference` |
| "Which approach is better?" | §15 → `blockchain-reference` (contested) |
| "Is this still current?" | §16 → `blockchain-reference` |
| Docs, books, people | §17 → `blockchain-reference` |

---
