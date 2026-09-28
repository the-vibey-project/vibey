---
id: skill-19-sources-and-method-adb0500e48
purpose: 19 sources and method
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-reference/SKILL.md
requires: ["skill-18-quick-reference-e41f8c5e7b"]
links: []
---

## §19. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §1.1 → `blockchain-protocol-layer`, §4 → `blockchain-smart-contract-development` (EVM model),
§6.3 → `blockchain-smart-contract-development` (design principles), §7.1 → `blockchain-smart-contract-development`, §8.2 → `blockchain-smart-contract-development`–8.3, §10.2 → `blockchain-security-testing-and-ops` (the vulnerability canon), §12 → `blockchain-protocol-layer`, §14 — rests
on protocol specifications, the standard security references in §17, and vulnerability
classes documented consistently across years of post-mortems. Every **time-sensitive**
claim (upgrade schedules, client shares, compiler versions, tooling benchmarks, exploit
statistics) was verified against a primary or near-primary source in **August 2026** and is
flagged in §16 with a decay-risk rating. Where sources conflict — notably the Glamsterdam
date and the client-share numbers — **I have reported the conflict rather than picking one**.

**Search log** (August 2026): Ethereum roadmap, Fusaka, and Glamsterdam status · Solidity
versions and the Foundry/Hardhat toolchain · smart contract exploit statistics and audit
landscape · execution client diversity and the L2/rollup client layer.

**Primary and near-primary sources consulted (selected):**
- **ethereum.org** — the roadmap, Fusaka and Glamsterdam pages, client diversity docs,
  nodes-and-clients, and the "Building on Ethereum in 2026" post (gas environment)
- **Solidity** — the official releases blog (0.8.36, July 2026) and Etherscan's compiler
  version list for nightly state
- **OWASP Smart Contract Top 10 (2026)** — the loss-category breakdown, built from 2025
  incident data via SolidityScan's Web3HackHub
- **Chainalysis** — the unverified-contracts analysis and threat-actor attribution;
  **Hacken** quarterly security reporting; **DefiLlama** hacks database for the YoY change
- **Ethernodes**, **Chainstack**, **clientdiversity.org**, and **EthStaker's 2026 staking
  landscape analysis** for client share (all four disagree; all four are cited)
- **Stakely**'s post-mortem of the September 2025 Reth incident
- **Nomic Foundation / Hardhat 3** documentation and independent Foundry-vs-Hardhat
  benchmark write-ups; **Foundry**'s configuration reference
- **The Block**, **CoinDesk**, **Decrypt**, **Everstake**, and **Chainstack** on upgrade
  naming, scope, and infrastructure implications

**Confidence statement.** **High confidence** in §1 → `blockchain-protocol-layer`, §4–§8 → `blockchain-smart-contract-development`, §10.2 → `blockchain-security-testing-and-ops`, §12 → `blockchain-protocol-layer`, §13 → `blockchain-security-testing-and-ops`, §14 and §18 —
these rest on protocol specifications, official documentation, and vulnerability classes
documented across many years of incidents. **High confidence** in the Solidity version
details and in Fusaka's activation date, both from official sources. **Moderate confidence,
and explicitly conflicted, on the Glamsterdam timeline** (§3.2 → `blockchain-protocol-layer`, §16): official Ethereum
material and secondary coverage give different dates ranging from H1 2026 to Q4 2026,
developers consistently caveat that it depends on testnet validation, and I have presented
that spread rather than a single date. **Moderate confidence on client-share figures**
(§1.3 → `blockchain-protocol-layer`, §16): four sources give materially different numbers because they measure different
populations, and I have reported all four rather than averaging them. **Moderate confidence
on the exploit statistics** (§10.1 → `blockchain-security-testing-and-ops`): these come from security firms and analytics platforms
with differing methodologies and incentives, aggregate loss figures for a given period vary
substantially between trackers, and attribution to specific threat actors is inherently
uncertain — **the ordering of loss categories is well-corroborated across sources and is
the part I would rely on; the precise dollar figures are not.** Tooling benchmark claims in
§9.1 → `blockchain-security-testing-and-ops` come from third-party comparisons rather than a standing neutral benchmark, and
Foundry maintains its own benchmark page while Hardhat does not, which is itself a source
of asymmetry. **Nothing in this document is investment advice**, and no claim here should
be read as an assessment of any asset's value.
