---
id: skill-18-quick-reference-e41f8c5e7b
purpose: 18 quick reference
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-reference/SKILL.md
requires: ["skill-17-the-canon-600cf8c87f"]
links: ["skill-19-sources-and-method-adb0500e48"]
---

## §18. Quick Reference

### 18.1 Numbers
- **21,000 gas** base transaction; **4/16 gas** per zero/non-zero calldata byte.
- **Cold SLOAD ~2,100 · zero→nonzero SSTORE ~20,000 · nonzero→nonzero ~2,900.**
- **63/64 rule** on forwarded gas (EIP-150).
- Stack depth **1024**; word size **256 bits**.
- Ethereum finality: **2 epochs ≈ 13 minutes**.
- Validator: **32 ETH**; max effective balance **2048 ETH** post-EIP-7251.
- Optimistic rollup withdrawal: **~7 days**.
- Client-diversity thresholds: **>1/3 breaks finality, >2/3 can finalize a bad chain.**
- Access control ≈ **$953M** of 2025's ~$1.42B in losses.

### 18.2 Pre-deployment checklist
- [ ] Exact solc version pinned; optimizer settings recorded; build reproducible
- [ ] Every privileged function has the right modifier, on **every** path
- [ ] Initializers protected; implementation contracts have `_disableInitializers()`
- [ ] Storage layout append-only (or ERC-7201) if upgradeable
- [ ] Checks-Effects-Interactions everywhere; reentrancy guards where needed
- [ ] All external calls' return values checked; `SafeERC20` for tokens
- [ ] Oracles: no spot prices, staleness checked, sequencer uptime checked on L2
- [ ] Every loop bounded; pull-over-push for payments
- [ ] Slippage bounds and deadlines on anything swapping
- [ ] Fuzz + **invariant** tests written and passing; Slither clean or triaged
- [ ] Fork tests against real mainnet state and dependencies
- [ ] Audited; findings fixed **and root-caused**; re-audited after changes
- [ ] Ownership on a multisig + timelock, never an EOA
- [ ] Source verified on the explorer
- [ ] Monitoring, pause procedure, and incident runbook live **before** launch
- [ ] Bug bounty posted

### 18.3 Triage
| Symptom | First look |
|---|---|
| Transaction reverts, no reason | `debug_traceTransaction` on an archive node; check custom errors |
| "Out of gas" on a working function | Unbounded loop over a grown array (§4.2 → `blockchain-smart-contract-development`) |
| Works on mainnet, fails on another EVM chain | Different gas schedule/opcodes (§4.3 → `blockchain-smart-contract-development`) |
| Integration breaks on one specific token | Non-standard ERC-20 (§7.1 → `blockchain-smart-contract-development`) |
| Upgrade corrupted state | Storage layout collision (§6.1 → `blockchain-smart-contract-development`) |
| Users report losing funds without a contract bug | Phishing / signature approval — check what they signed (§10.1 → `blockchain-security-testing-and-ops`, §13.4 → `blockchain-security-testing-and-ops`) |
| Indexer data is wrong | Reorg handling (§13.4 → `blockchain-security-testing-and-ops`) |
| Validator missing attestations at a fork | Client not updated for the fork (§3.1 → `blockchain-protocol-layer`) |
| Price feed returns something absurd | Staleness, or manipulation of a spot source (§8.2 → `blockchain-smart-contract-development`) |

---
