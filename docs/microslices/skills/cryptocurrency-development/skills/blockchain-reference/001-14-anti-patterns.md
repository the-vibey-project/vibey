---
id: skill-14-anti-patterns-d03ebea940
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-reference/SKILL.md
requires: []
links: ["skill-15-contested-questions-9ccfe96fc7"]
---

## §14. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Assuming your function is only called your way | Every function is public to the world, in any order | Design adversarially (§0 → `blockchain-protocol-layer` framing 1) |
| Focusing security effort on reentrancy | It's ~$35.7M vs access control's ~$953.2M | **Audit every privileged path** (§10.1 → `blockchain-security-testing-and-ops`) |
| Treating an audit as a guarantee | One breached protocol had passed 18 | Audits + fuzzing + invariants + monitoring (§9 → `blockchain-security-testing-and-ops`, §10.3 → `blockchain-security-testing-and-ops`) |
| Security budget entirely on code | Phishing/social engineering was ~2/3 of Q1 2026 losses | Key management and opsec as first-class (§10.1 → `blockchain-security-testing-and-ops`) |
| Floating pragma in production | Non-reproducible bytecode | Pin the exact solc version (§5.1 → `blockchain-smart-contract-development`) |
| Leaving contracts on Solidity <0.8 | No automatic overflow protection | Migrate; a 2026 exploit hit 0.6.10 code (§5.1 → `blockchain-smart-contract-development`) |
| `tx.origin` for authorization | Trivially phishable | `msg.sender` (§5.1 → `blockchain-smart-contract-development`) |
| External call before state update | Reentrancy | **Checks-Effects-Interactions** (§6.3 → `blockchain-smart-contract-development`) |
| Spot price from a DEX pool as an oracle | One flash loan moves it | Chainlink/TWAP/multi-source (§8.2 → `blockchain-smart-contract-development`) |
| Not checking oracle staleness | A stale price is itself an exploit | Check `updatedAt`, sequencer uptime (§8.2 → `blockchain-smart-contract-development`) |
| Assuming ERC-20 compliance | Non-standard returns, fees, rebases, 6 decimals, blocklists | `SafeERC20`; measure balance deltas (§7.1 → `blockchain-smart-contract-development`) |
| Hardcoding 18 decimals | USDC has 6 | Read `decimals()` |
| Unbounded loop over user-controlled array | **Permanent DoS**; funds can lock forever | Bound it; pull over push (§4.2 → `blockchain-smart-contract-development`, §6.3 → `blockchain-smart-contract-development`) |
| Pushing payments to users | One reverting recipient blocks everyone | Pull pattern (§6.3 → `blockchain-smart-contract-development`) |
| Swap with no slippage bound or deadline | Free money for a sandwicher | Always set both (§8.4 → `blockchain-smart-contract-development`) |
| On-chain randomness from block data | Miners/proposers and everyone else can see it | VRF (§10.2 → `blockchain-security-testing-and-ops`) |
| Reordering storage variables in an upgrade | **Storage collision corrupts state** | Append-only; ERC-7201 (§6.1 → `blockchain-smart-contract-development`) |
| Leaving an implementation contract uninitialized | Someone else initializes; UUPS can be bricked | `_disableInitializers()` (§6.1 → `blockchain-smart-contract-development`) |
| Constructor logic in an upgradeable contract | Constructors don't run in proxy context | `initialize()` with a guard (§6.1 → `blockchain-smart-contract-development`) |
| Single-step ownership transfer | A typo'd address orphans the contract forever | `Ownable2Step` (§6.2 → `blockchain-smart-contract-development`) |
| Owner as an EOA on a live protocol | One key, one compromise, total loss | Multisig + timelock (§6.2 → `blockchain-smart-contract-development`, §13.2 → `blockchain-security-testing-and-ops`) |
| Leaving contracts unverified | ~$36.7M lost across five such protocols; decompilation is easy anyway | Verify on the explorer (§10.3 → `blockchain-security-testing-and-ops`) |
| Deploying to another EVM chain without re-review | Different gas costs and opcodes | Re-audit per chain (§4.3 → `blockchain-smart-contract-development`) |
| Trusting an inbound cross-chain message | Fake messages passing validation is a live 2026 pattern | Verify sender **and** source chain (§12 → `blockchain-protocol-layer`) |
| Believing "decentralized" without checking | Most rollups have one sequencer; many bridges are a multisig | L2Beat stages; state the trust model (§11.1 → `blockchain-protocol-layer`, §12 → `blockchain-protocol-layer`) |
| Assuming 2021-era gas prices | Mainnet ran ~0.15 gwei in May 2026 | Do the gas math (§3.3 → `blockchain-protocol-layer`) |
| Blind-signing multisig transactions | How multisig holders get drained | Verify calldata (§13.2 → `blockchain-security-testing-and-ops`) |
| Running one validator key on two machines | Self-inflicted slashing | Slashing protection discipline (§13.3 → `blockchain-security-testing-and-ops`) |
| Running the supermajority client | Systemic risk, and Reth's 2025 outage shows the personal one | Minority client (§1.3 → `blockchain-protocol-layer`) |
| Under-emitting events | Your off-chain systems can't see state | Emit for everything indexed (§13.4 → `blockchain-security-testing-and-ops`) |
| Indexer that ignores reorgs | Serves data that got un-happened | Handle reorgs (§13.4 → `blockchain-security-testing-and-ops`) |

---
